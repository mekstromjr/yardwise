import datetime

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.urls import reverse

from garden.irrigation_today import needs_repair_count, zones_for_bed
from garden.models import (
    Bed,
    ComponentCondition,
    ComponentType,
    EventType,
    InvestigationStatus,
    IrrigationComponent,
    IrrigationEvent,
    IrrigationZone,
    ZoneStatus,
    ZoneType,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_client(client):
    user = User.objects.create_user("michele", password="x")
    client.force_login(user)
    return client


# --- IrrigationZone ---------------------------------------------------------


def test_zone_codes_are_sequential_and_immutable_across_rename():
    z1 = IrrigationZone.objects.create(name="Unknown Zone 1")
    z2 = IrrigationZone.objects.create(name="Unknown Zone 2")
    assert (z1.code, z2.code) == ("ZONE-01", "ZONE-02")
    z1.name = "Front Lawn Rotors"
    z1.save()
    z1.refresh_from_db()
    assert z1.code == "ZONE-01"


def test_zone_defaults_are_honest_unknowns():
    zone = IrrigationZone.objects.create(name="Unknown Zone 1")
    assert zone.zone_type == ZoneType.UNKNOWN
    assert zone.investigation_status == InvestigationStatus.UNKNOWN
    assert zone.status == ZoneStatus.UNKNOWN
    assert zone.controller_station is None
    assert zone.last_verified_on is None


# --- IrrigationComponent ----------------------------------------------------


def test_component_without_zone_is_valid():
    component = IrrigationComponent.objects.create(
        component_type=ComponentType.VALVE, location_note="mystery valve box by driveway"
    )
    assert component.zone is None
    assert component.condition == ComponentCondition.UNKNOWN
    assert "mystery valve box" in str(component)
    bare = IrrigationComponent.objects.create(component_type=ComponentType.HEAD)
    assert "unassigned" in str(bare)


# --- IrrigationEvent --------------------------------------------------------


def test_event_requires_zone_or_component():
    with pytest.raises(IntegrityError):
        IrrigationEvent.objects.create(
            event_type=EventType.OBSERVATION, happened_on=datetime.date.today()
        )


def test_event_with_only_component_is_valid():
    component = IrrigationComponent.objects.create(component_type=ComponentType.HEAD)
    event = IrrigationEvent.objects.create(
        component=component,
        event_type=EventType.REPAIR,
        happened_on=datetime.date.today(),
        notes="replaced the nozzle",
    )
    assert event.zone is None


# --- Views ------------------------------------------------------------------


def test_irrigation_views_require_login(client):
    for name in ("irrigation-overview", "irrigation-zone-add", "irrigation-event-add"):
        assert client.get(reverse(name)).status_code == 302


def test_overview_groups_by_investigation_status_and_lists_unassigned(user_client):
    IrrigationZone.objects.create(name="Mystery Zone")
    IrrigationZone.objects.create(
        name="Front Lawn", investigation_status=InvestigationStatus.VERIFIED
    )
    IrrigationComponent.objects.create(
        component_type=ComponentType.VALVE, location_note="valve box by the porch"
    )
    r = user_client.get(reverse("irrigation-overview"))
    content = r.content.decode()
    assert r.status_code == 200
    # Unknown group leads; Verified follows.
    assert content.index("Mystery Zone") < content.index("Front Lawn")
    assert "Components without a zone" in content
    assert "valve box by the porch" in content


def test_zone_add_with_only_name_gets_unknown_defaults(user_client):
    r = user_client.post(reverse("irrigation-zone-add"), {
        "name": "Unknown Zone 1",
        "zone_type": ZoneType.UNKNOWN,
        "investigation_status": InvestigationStatus.UNKNOWN,
        "status": ZoneStatus.UNKNOWN,
    })
    zone = IrrigationZone.objects.get()
    assert r.status_code == 302
    assert zone.code == "ZONE-01"
    assert zone.investigation_status == InvestigationStatus.UNKNOWN


def test_investigation_status_flows_unknown_to_verified(user_client):
    zone = IrrigationZone.objects.create(name="Back Beds Drip")
    r = user_client.post(reverse("irrigation-zone-edit", args=[zone.pk]), {
        "name": "Back Beds Drip",
        "zone_type": ZoneType.DRIP,
        "investigation_status": InvestigationStatus.VERIFIED,
        "status": ZoneStatus.ACTIVE,
        "last_verified_on": datetime.date.today().isoformat(),
    })
    zone.refresh_from_db()
    assert r.status_code == 302
    assert zone.investigation_status == InvestigationStatus.VERIFIED
    assert zone.last_verified_on == datetime.date.today()
    assert zone.code == "ZONE-01"  # permanent ID survives the whole flow


def test_zone_detail_shows_served_bed_chips_and_component_history(user_client):
    bed = Bed.objects.create(name="Blueberry Bed")
    zone = IrrigationZone.objects.create(name="Berry Drip", zone_type=ZoneType.DRIP)
    zone.beds.add(bed)
    component = IrrigationComponent.objects.create(
        zone=zone, component_type=ComponentType.EMITTER
    )
    IrrigationEvent.objects.create(
        component=component,
        event_type=EventType.REPAIR,
        happened_on=datetime.date.today(),
        notes="unclogged the emitter",
    )
    r = user_client.get(reverse("irrigation-zone-detail", args=[zone.pk]))
    content = r.content.decode()
    assert "Blueberry Bed" in content
    assert reverse("bed-detail", args=[bed.pk]) in content
    assert "unclogged the emitter" in content  # component events roll up to the zone


def test_event_form_rejects_neither_zone_nor_component(user_client):
    r = user_client.post(reverse("irrigation-event-add"), {
        "event_type": EventType.OBSERVATION,
        "happened_on": datetime.date.today().isoformat(),
    })
    assert r.status_code == 200  # re-rendered with errors, nothing saved
    assert IrrigationEvent.objects.count() == 0
    assert b"a zone, a component, or both" in r.content


def test_event_add_via_form(user_client):
    zone = IrrigationZone.objects.create(name="Front Lawn")
    r = user_client.post(reverse("irrigation-event-add"), {
        "zone": zone.pk,
        "event_type": EventType.WINTERIZATION,
        "happened_on": datetime.date.today().isoformat(),
        "notes": "blew out the lines",
    })
    event = IrrigationEvent.objects.get()
    assert r.status_code == 302
    assert event.created_by.username == "michele"
    assert event.zone == zone


def test_archived_zone_leaves_overview_but_row_survives(user_client):
    import django.utils.timezone as tz

    zone = IrrigationZone.objects.create(name="Old Zone")
    zone.archived_at = tz.now()
    zone.save(update_fields=["archived_at"])
    r = user_client.get(reverse("irrigation-overview"))
    assert b"Old Zone" not in r.content
    assert IrrigationZone.objects.filter(pk=zone.pk).exists()  # archive, never delete


# --- Bed-detail helpers -----------------------------------------------------


def test_zones_for_bed_and_needs_repair_count():
    bed = Bed.objects.create(name="Kitchen Garden")
    zone = IrrigationZone.objects.create(name="Veg Drip", status=ZoneStatus.NEEDS_REPAIR)
    zone.beds.add(bed)
    IrrigationComponent.objects.create(
        component_type=ComponentType.HEAD, condition=ComponentCondition.BROKEN
    )
    IrrigationComponent.objects.create(
        component_type=ComponentType.HEAD, condition=ComponentCondition.GOOD
    )
    assert list(zones_for_bed(bed)) == [zone]
    assert needs_repair_count() == 2  # the flagged zone + the broken head
