import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden.models import (
    Bed,
    ClimateProfile,
    CropFamily,
    GrowingMethod,
    HarvestEvent,
    Plant,
    PlantingStatus,
    SeasonalPlanting,
    Variety,
)
from garden.planner_today import due_milestones

pytestmark = pytest.mark.django_db


@pytest.fixture
def climate():
    profile = ClimateProfile.load()
    profile.hardiness_zone = "8b"
    profile.avg_last_frost_month = 4
    profile.avg_last_frost_day = 15
    profile.avg_first_frost_month = 11
    profile.avg_first_frost_day = 1
    profile.save()
    return profile


@pytest.fixture
def tomato():
    return Variety.objects.create(
        name="Tomato",
        cultivar="Stupice",
        crop_family=CropFamily.NIGHTSHADE,
        days_to_maturity=60,
        start_indoors_weeks_before_lf=6,
        transplant_weeks_after_lf=2,
    )


@pytest.fixture
def peas():
    return Variety.objects.create(
        name="Snap pea",
        crop_family=CropFamily.LEGUME,
        direct_sow_weeks=-4,  # four weeks BEFORE last frost
    )


@pytest.fixture
def user_client(client):
    user = User.objects.create_user("michele", password="x")
    client.force_login(user)
    return client


# --- ClimateProfile ---------------------------------------------------------


def test_climate_profile_is_a_singleton_with_frost_helpers(climate):
    assert ClimateProfile.load().pk == climate.pk
    assert climate.last_frost_date(2026) == datetime.date(2026, 4, 15)
    assert climate.first_frost_date(2026) == datetime.date(2026, 11, 1)


def test_unset_climate_yields_none_not_a_fake_date():
    profile = ClimateProfile.load()
    assert profile.last_frost_date(2026) is None
    assert profile.first_frost_date(2026) is None


# --- Milestone computation (PDD 6.6 / 6.10) ---------------------------------


def test_seed_indoors_milestones(climate, tomato):
    p = SeasonalPlanting.objects.create(
        variety=tomato, year=2026, growing_method=GrowingMethod.SEED_INDOORS
    )
    labels = dict(p.milestones)
    assert labels["Start seeds indoors"] == datetime.date(2026, 3, 4)  # LF - 6 weeks
    assert labels["Transplant outdoors"] == datetime.date(2026, 4, 29)  # LF + 2 weeks
    # Harvest estimated from the computed transplant date + days to maturity
    assert labels["Expected first harvest"] == datetime.date(2026, 6, 28)


def test_direct_sow_milestones_handle_negative_offsets(climate, peas):
    p = SeasonalPlanting.objects.create(
        variety=peas, year=2026, growing_method=GrowingMethod.DIRECT_SOW
    )
    assert p.milestones == [("Direct sow", datetime.date(2026, 3, 18))]  # LF - 4 weeks


def test_purchase_starts_gets_buy_plant_only_no_seed_nagging(climate, tomato):
    p = SeasonalPlanting.objects.create(
        variety=tomato, year=2026, growing_method=GrowingMethod.PURCHASE_STARTS
    )
    labels = [label for label, _date in p.milestones]
    assert "Buy and plant starts" in labels
    assert "Start seeds indoors" not in labels  # PDD 6.10: method-appropriate only


def test_undecided_shows_both_option_timelines(climate, tomato):
    tomato.direct_sow_weeks = 0
    tomato.save()
    p = SeasonalPlanting.objects.create(
        variety=tomato, year=2026, growing_method=GrowingMethod.UNDECIDED
    )
    labels = [label for label, _date in p.milestones]
    assert "If starting indoors: start seeds" in labels
    assert "If direct sowing: sow" in labels


def test_no_climate_profile_means_no_milestones_not_guesses(tomato):
    p = SeasonalPlanting.objects.create(
        variety=tomato, year=2026, growing_method=GrowingMethod.SEED_INDOORS
    )
    assert p.milestones == []


def test_actual_sow_date_wins_over_estimate_for_harvest(climate, peas):
    peas.days_to_maturity = 60
    peas.save()
    p = SeasonalPlanting.objects.create(
        variety=peas, year=2026, growing_method=GrowingMethod.DIRECT_SOW,
        sowed_on=datetime.date(2026, 4, 1),
    )
    labels = dict(p.milestones)
    assert labels["Expected first harvest"] == datetime.date(2026, 5, 31)


# --- Crop rotation (PDD 6.3) ------------------------------------------------


def make_planting(variety, year, bed, **kwargs):
    return SeasonalPlanting.objects.create(variety=variety, year=year, bed=bed, **kwargs)


def test_rotation_warns_within_three_years_same_family_same_bed(climate, tomato):
    bed = Bed.objects.create(name="Veg Bed 1")
    pepper = Variety.objects.create(name="Pepper", crop_family=CropFamily.NIGHTSHADE)
    old = make_planting(pepper, 2024, bed, status=PlantingStatus.FINISHED)
    planned = make_planting(tomato, 2026, bed)
    assert list(planned.rotation_conflicts()) == [old]


def test_rotation_ignores_old_years_other_beds_other_families(climate, tomato, peas):
    bed = Bed.objects.create(name="Veg Bed 1")
    other_bed = Bed.objects.create(name="Veg Bed 2")
    make_planting(tomato, 2022, bed)  # 4 years back: outside the window
    make_planting(tomato, 2025, other_bed)  # different bed
    make_planting(peas, 2025, bed)  # different family
    planned = make_planting(tomato, 2026, bed)
    assert not planned.rotation_conflicts().exists()


def test_rotation_needs_a_bed_and_a_known_family(climate):
    mystery = Variety.objects.create(name="Mystery gourd")  # family unknown
    p = SeasonalPlanting.objects.create(variety=mystery, year=2026)
    assert not p.rotation_conflicts().exists()


# --- Screens ----------------------------------------------------------------


def test_planner_screens_require_login(client, tomato):
    for url in (reverse("planner"), reverse("variety-list"), reverse("planner-climate")):
        assert client.get(url).status_code == 302


def test_planner_home_groups_by_bed_and_shows_rotation_chip(user_client, climate, tomato):
    bed = Bed.objects.create(name="Veg Bed 1")
    make_planting(tomato, 2024, bed, status=PlantingStatus.FINISHED)
    make_planting(tomato, 2026, bed, growing_method=GrowingMethod.SEED_INDOORS)
    r = user_client.get(reverse("planner"), {"year": 2026})
    content = r.content.decode()
    assert r.status_code == 200
    assert "Veg Bed 1" in content
    assert "Start seeds indoors" in content  # milestone chip
    assert "Rotation:" in content  # warning chip, ignorable by design


def test_mark_as_planted_sets_status_and_method_appropriate_date(user_client, climate, peas):
    p = SeasonalPlanting.objects.create(
        variety=peas, year=2026, growing_method=GrowingMethod.DIRECT_SOW
    )
    r = user_client.post(reverse("planting-planted", args=[p.pk]))
    p.refresh_from_db()
    assert r.status_code == 302
    assert p.status == PlantingStatus.PLANTED
    assert p.sowed_on == datetime.date.today()
    assert p.transplanted_on is None  # direct sow records a sow date, not a transplant


def test_close_season_sets_finished_and_grow_again(user_client, climate, tomato):
    p = SeasonalPlanting.objects.create(variety=tomato, year=2026)
    r = user_client.post(
        reverse("planting-close", args=[p.pk]),
        {"grow_again": "yes", "closing_note": "Great year - two plants next time."},
    )
    p.refresh_from_db()
    assert r.status_code == 302
    assert p.status == PlantingStatus.FINISHED
    assert p.grow_again == "yes"
    assert "Great year" in p.season_notes
    tomato.refresh_from_db()
    assert tomato.archived_at is None  # variety library untouched by closing


def test_variety_add_and_list(user_client):
    r = user_client.post(reverse("variety-add"), {
        "name": "Zucchini", "crop_family": "cucurbit", "direct_sow_weeks": "1",
    })
    assert r.status_code == 302
    r = user_client.get(reverse("variety-list"))
    assert b"Zucchini" in r.content


def test_climate_form_edits_the_singleton(user_client):
    r = user_client.post(reverse("planner-climate"), {
        "hardiness_zone": "8b",
        "avg_last_frost_month": "4", "avg_last_frost_day": "15",
        "avg_first_frost_month": "11", "avg_first_frost_day": "1",
    })
    assert r.status_code == 302
    assert ClimateProfile.objects.count() == 1
    from garden.models import Garden

    garden = Garden.objects.get(owner__username="michele")
    assert ClimateProfile.load(garden).last_frost_date(2027) == datetime.date(2027, 4, 15)


def test_planting_form_renders_and_saves(user_client, climate, tomato):
    assert user_client.get(reverse("planting-add")).status_code == 200
    r = user_client.post(reverse("planting-add"), {
        "variety": tomato.pk, "year": "2026",
        "growing_method": "seed_indoors", "status": "planned",
    })
    assert r.status_code == 302
    p = SeasonalPlanting.objects.get()
    assert p.created_by.username == "michele"


# --- Harvest integration (PDD 6.12) -----------------------------------------


def test_harvest_event_can_link_to_a_seasonal_planting(climate, tomato):
    plant = Plant.objects.create(common_name="Tomato")
    p = SeasonalPlanting.objects.create(variety=tomato, year=2026)
    h = HarvestEvent.objects.create(
        plant=plant, harvested_on=datetime.date(2026, 7, 20), seasonal_planting=p
    )
    assert list(p.harvests.all()) == [h]


# --- Today helper (garden/planner_today.py) ---------------------------------


def test_due_milestones_windows_and_excludes_finished(climate, tomato, peas):
    active = SeasonalPlanting.objects.create(
        variety=peas, year=2026, growing_method=GrowingMethod.DIRECT_SOW
    )  # sow due 2026-03-18
    SeasonalPlanting.objects.create(
        variety=tomato, year=2026, growing_method=GrowingMethod.SEED_INDOORS,
        status=PlantingStatus.FINISHED,
    )
    items = due_milestones(on=datetime.date(2026, 3, 10), horizon_days=14)
    assert [(i.label, i.date, i.planting) for i in items] == [
        ("Direct sow", datetime.date(2026, 3, 18), active)
    ]
    assert due_milestones(on=datetime.date(2026, 7, 1), horizon_days=14) == []
