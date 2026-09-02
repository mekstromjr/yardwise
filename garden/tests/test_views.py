import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden.models import Bed, Plant, ScheduleKind, Task

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_client(client):
    user = User.objects.create_user("michele", password="x")
    client.force_login(user)
    return client


def test_views_require_login(client):
    for name in ("today", "plant-list", "plant-add"):
        assert client.get(reverse(name)).status_code == 302


def test_today_empty_state(user_client):
    r = user_client.get(reverse("today"))
    assert r.status_code == 200
    assert b"ready to grow" in r.content


def test_today_buckets_overdue_due_and_soon(user_client):
    Plant.objects.create(common_name="Pear")
    today = datetime.date.today()
    for title, due in [
        ("Overdue job", today - datetime.timedelta(days=3)),
        ("Due job", today),
        ("Soon job", today + datetime.timedelta(days=5)),
        ("Far job", today + datetime.timedelta(days=90)),
    ]:
        t = Task.objects.create(title=title, schedule_kind=ScheduleKind.EXACT_ONCE, due_on=due)
        t.create_initial_occurrence()
    r = user_client.get(reverse("today"))
    content = r.content.decode()
    assert content.index("Overdue job") < content.index("Due job") < content.index("Soon job")
    assert "Far job" not in content


def test_plant_add_with_only_name_then_appears_in_list(user_client):
    r = user_client.post(reverse("plant-add"), {"common_name": "Fuyu Persimmon",
                                                "planted_precision": "exact",
                                                "is_ornamental": "on"})
    plant = Plant.objects.get()
    assert r.status_code == 302
    assert plant.created_by.username == "michele"
    r = user_client.get(reverse("plant-list"))
    assert b"Fuyu Persimmon" in r.content


def test_plant_search_filters(user_client):
    Plant.objects.create(common_name="Blueberry")
    Plant.objects.create(common_name="Pear")
    r = user_client.get(reverse("plant-list"), {"q": "blue"})
    assert b"Blueberry" in r.content and b"Pear" not in r.content


def test_editing_location_creates_history_not_overwrite(user_client):
    bed1 = Bed.objects.create(name="Front Bed")
    bed2 = Bed.objects.create(name="Back Bed")
    base = {"common_name": "Rose", "planted_precision": "exact", "is_ornamental": "on"}
    user_client.post(reverse("plant-add"), {**base, "bed": bed1.pk})
    plant = Plant.objects.get()
    user_client.post(reverse("plant-edit", args=[plant.pk]), {**base, "bed": bed2.pk})
    locs = plant.locations.order_by("id")
    assert locs.count() == 2
    assert not locs[0].is_current and locs[0].ended_on
    assert locs[1].is_current and locs[1].bed == bed2


def test_same_bed_note_edit_does_not_create_history(user_client):
    bed = Bed.objects.create(name="Front Bed")
    base = {"common_name": "Rose", "planted_precision": "exact", "is_ornamental": "on"}
    user_client.post(reverse("plant-add"), {**base, "bed": bed.pk})
    plant = Plant.objects.get()
    payload = {**base, "bed": bed.pk, "location_note": "north edge"}
    user_client.post(reverse("plant-edit", args=[plant.pk]), payload)
    assert plant.locations.count() == 1
    assert plant.locations.get().location_note == "north edge"
