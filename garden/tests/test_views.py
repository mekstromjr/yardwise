import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden.models import (
    Bed,
    Photo,
    PhotoCategory,
    Plant,
    PlantLocation,
    PlantStatus,
    ScheduleKind,
    Tag,
    Task,
)

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


def test_plant_add_offers_photo_picker_and_drag_drop(user_client):
    r = user_client.get(reverse("plant-add"))

    assert r.status_code == 200
    assert b"Drag a plant photo here" in r.content
    assert b"choose from Photos or files" in r.content
    assert b"Remove selected photo" in r.content
    assert b"data-photo-remove hidden" in r.content
    assert b"js/photo-picker.js" in r.content


def test_plant_search_filters(user_client):
    Plant.objects.create(common_name="Blueberry")
    Plant.objects.create(common_name="Pear")
    r = user_client.get(reverse("plant-list"), {"q": "blue"})
    assert b"Blueberry" in r.content and b"Pear" not in r.content


def test_plant_live_search_preserves_the_active_input(user_client):
    response = user_client.get(reverse("plant-list"), {"q": "blue"})

    assert response.status_code == 200
    assert b'id="plant-search"' in response.content
    assert b"hx-preserve" in response.content
    assert b'hx-sync="this:replace"' in response.content
    assert b'value="blue"' in response.content


def test_show_on_map_disabled_without_current_map_point(user_client):
    plant = Plant.objects.create(common_name="Rose")
    profile_url = reverse("plant-detail", args=[plant.pk])
    map_url = reverse("map") + f"?plant={plant.pk}"

    response = user_client.get(profile_url)
    assert b'Show on map</span>' in response.content

    bed = Bed.objects.create(name="Front border")
    location = PlantLocation.objects.create(plant=plant, bed=bed)

    response = user_client.get(profile_url)
    assert response.status_code == 200
    assert b'Show on map</span>' in response.content
    assert b'aria-disabled="true" title="Set a map location to enable this"' in response.content
    assert f'href="{map_url}">Show on map</a>'.encode() not in response.content
    assert b"Set/change map location" in response.content

    location.point_x = 0
    location.save(update_fields=["point_x"])
    response = user_client.get(profile_url)
    assert b'Show on map</span>' in response.content

    location.point_y = 0
    location.save(update_fields=["point_y"])
    response = user_client.get(profile_url)
    assert f'href="{map_url}">Show on map</a>'.encode() in response.content

    location.is_current = False
    location.save(update_fields=["is_current"])
    response = user_client.get(profile_url)
    assert b'Show on map</span>' in response.content


def test_plant_list_has_sticky_alphabet_links_to_first_matching_card(user_client):
    Plant.objects.create(common_name="Azalea")
    Plant.objects.create(common_name="Blueberry")
    Plant.objects.create(common_name="Bee balm")
    Plant.objects.create(common_name="Rose")

    response = user_client.get(reverse("plant-list"))

    assert response.status_code == 200
    assert b'class="plant-alphabet"' in response.content
    assert b'href="#plants-A"' in response.content
    assert b'href="#plants-B"' in response.content
    assert b'href="#plants-R"' in response.content
    assert b'href="#plants-C"' not in response.content
    assert response.content.count(b'id="plants-B"') == 1
    assert b'<span aria-disabled="true">C</span>' in response.content


def test_plant_alphabet_reflects_search_results(user_client):
    Plant.objects.create(common_name="Azalea")
    Plant.objects.create(common_name="Blueberry")

    response = user_client.get(reverse("plant-list"), {"q": "blue"})

    assert b'href="#plants-B"' in response.content
    assert b'href="#plants-A"' not in response.content
    assert b'<span aria-disabled="true">A</span>' in response.content


def test_plant_filters_can_be_combined(user_client):
    bed = Bed.objects.create(name="Kitchen Garden")
    other_bed = Bed.objects.create(name="Front Border")
    edible_tag = Tag.objects.create(name="Preserving")
    berry_type = Plant._meta.get_field("plant_type").related_model.objects.create(name="Berry")

    blueberry = Plant.objects.create(
        common_name="Blueberry", plant_type=berry_type, is_edible=True, is_ornamental=True
    )
    blueberry.tags.add(edible_tag)
    PlantLocation.objects.create(plant=blueberry, bed=bed)
    rose = Plant.objects.create(common_name="Rose", plant_type=berry_type, is_edible=False)
    rose.tags.add(edible_tag)
    PlantLocation.objects.create(plant=rose, bed=other_bed)

    r = user_client.get(reverse("plant-list"), {
        "bed": bed.pk,
        "plant_type": berry_type.pk,
        "use": "edible",
        "tag": edible_tag.pk,
    })

    assert b"Blueberry" in r.content
    assert b"Rose" not in r.content
    assert r.context["result_count"] == 1


def test_plant_status_filter_defaults_to_active_and_can_show_archived(user_client):
    Plant.objects.create(common_name="Living Pear")
    Plant.objects.create(common_name="Old Pear", status=PlantStatus.ARCHIVED)

    default = user_client.get(reverse("plant-list"))
    assert b"Living Pear" in default.content and b"Old Pear" not in default.content

    archived = user_client.get(reverse("plant-list"), {"status": PlantStatus.ARCHIVED})
    assert b"Old Pear" in archived.content and b"Living Pear" not in archived.content


def test_plant_can_be_archived_and_restored(user_client):
    plant = Plant.objects.create(common_name="Rose")

    response = user_client.post(reverse("plant-archive", args=[plant.pk]))

    assert response.status_code == 302
    plant.refresh_from_db()
    assert plant.status == PlantStatus.ARCHIVED
    assert plant.archived_at is not None
    assert b"Rose" not in user_client.get(reverse("plant-list")).content

    response = user_client.post(reverse("plant-unarchive", args=[plant.pk]))

    assert response.status_code == 302
    plant.refresh_from_db()
    assert plant.status == PlantStatus.ACTIVE
    assert plant.archived_at is None


def test_plant_delete_is_post_only_and_permanent(user_client):
    plant = Plant.objects.create(common_name="Duplicate Rose")
    url = reverse("plant-delete", args=[plant.pk])

    assert user_client.get(url).status_code == 405
    response = user_client.post(url)

    assert response.status_code == 302
    assert not Plant.objects.filter(pk=plant.pk).exists()


def test_plant_detail_explains_archive_and_confirms_delete(user_client):
    plant = Plant.objects.create(common_name="Rose")

    response = user_client.get(reverse("plant-detail", args=[plant.pk]))

    assert b"Archive this plant" in response.content
    assert b"Delete this plant permanently" in response.content
    assert b"return confirm(" in response.content
    assert b"This cannot be undone" in response.content


def test_plant_edit_saves_free_text_care_recommendations(user_client):
    plant = Plant.objects.create(common_name="Blueberry")
    payload = {
        "common_name": "Blueberry",
        "planted_precision": "exact",
        "is_ornamental": "on",
        "spring_care": "Top-dress with compost after bloom.",
        "summer_care": "Water deeply during fruit development.",
        "fall_care": "Refresh mulch before cold weather.",
        "winter_care": "Inspect for broken branches.",
        "pruning_recommendations": "Remove the oldest canes in late winter.",
        "problems_to_watch": "Watch for mummy berry and spotted leaves.",
    }

    response = user_client.post(reverse("plant-edit", args=[plant.pk]), payload)

    assert response.status_code == 302
    plant.refresh_from_db()
    assert plant.spring_care == payload["spring_care"]
    assert plant.pruning_recommendations == payload["pruning_recommendations"]
    assert plant.problems_to_watch == payload["problems_to_watch"]


def test_plant_detail_shows_seasonal_care_pruning_and_problems(user_client):
    plant = Plant.objects.create(
        common_name="Blueberry",
        spring_care="Top-dress with compost.",
        pruning_recommendations="Prune in late winter.",
        problems_to_watch="Watch for mummy berry.",
    )

    response = user_client.get(reverse("plant-detail", args=[plant.pk]))

    assert b"Seasonal care" in response.content
    assert b"Top-dress with compost" in response.content
    assert b"Pruning recommendations" in response.content
    assert b"Problems to watch for" in response.content


def test_plant_detail_has_alphabetical_previous_and_next_navigation(user_client):
    apple = Plant.objects.create(common_name="Apple")
    bee_balm = Plant.objects.create(common_name="Bee Balm")
    cedar = Plant.objects.create(common_name="Cedar")
    archived = Plant.objects.create(common_name="Aardvark Fern", status=PlantStatus.ARCHIVED)

    response = user_client.get(reverse("plant-detail", args=[bee_balm.pk]))

    assert response.status_code == 200
    assert response.context["previous_plant"] == apple
    assert response.context["next_plant"] == cedar
    assert response.context["plant_position"] == 2
    assert response.context["plant_count"] == 3
    assert reverse("plant-detail", args=[apple.pk]).encode() in response.content
    assert reverse("plant-detail", args=[cedar.pk]).encode() in response.content
    assert b"Previous plant: Apple" in response.content
    assert b"Next plant: Cedar" in response.content
    assert archived.common_name.encode() not in response.content


def test_plant_profile_navigation_stops_at_the_ends(user_client):
    apple = Plant.objects.create(common_name="Apple")
    Plant.objects.create(common_name="Bee Balm")

    response = user_client.get(reverse("plant-detail", args=[apple.pk]))

    assert response.context["previous_plant"] is None
    assert response.context["next_plant"].common_name == "Bee Balm"
    assert b"Start of list" in response.content
    assert b"1 of 2" in response.content


def test_plant_filters_ignore_invalid_url_values(user_client):
    Plant.objects.create(common_name="Pear")

    r = user_client.get(reverse("plant-list"), {
        "bed": "not-a-number",
        "plant_type": "broken",
        "tag": "nope",
        "use": "invalid",
        "status": "unknown",
    })

    assert r.status_code == 200
    assert b"Pear" in r.content


def test_advanced_filters_are_collapsed_until_one_is_active(user_client):
    bed = Bed.objects.create(name="Kitchen Garden")
    plant = Plant.objects.create(common_name="Pear")
    PlantLocation.objects.create(plant=plant, bed=bed)

    default = user_client.get(reverse("plant-list"))
    assert not default.context["advanced_filters_active"]
    assert b'<details class="advanced-filters"' in default.content

    filtered = user_client.get(reverse("plant-list"), {"bed": bed.pk})
    assert filtered.context["advanced_filters_active"]
    assert b'<details class="advanced-filters" open>' in filtered.content
    assert b"Advanced filters" in filtered.content and b"active" in filtered.content


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


# --- Tasks UI ----------------------------------------------------------------


def test_task_list_views_split_due_and_upcoming(user_client):
    today = datetime.date.today()
    due = Task.objects.create(title="Water pots", schedule_kind=ScheduleKind.EXACT_ONCE,
                              due_on=today)
    due.create_initial_occurrence()
    later = Task.objects.create(title="Plant bulbs", schedule_kind=ScheduleKind.EXACT_ONCE,
                                due_on=today + datetime.timedelta(days=30))
    later.create_initial_occurrence()
    r = user_client.get(reverse("task-list"), {"view": "due"})
    assert b"Water pots" in r.content and b"Plant bulbs" not in r.content
    r = user_client.get(reverse("task-list"), {"view": "upcoming"})
    assert b"Plant bulbs" in r.content and b"Water pots" not in r.content


def test_task_create_form_generates_first_occurrence(user_client):
    r = user_client.post(reverse("task-add"), {
        "title": "Feed roses",
        "schedule_kind": "interval",
        "interval_count": 6, "interval_unit": "weeks",
        "interval_anchor": "after_completion",
        "priority": "medium",
    })
    assert r.status_code == 302
    task = Task.objects.get(title="Feed roses")
    assert task.occurrences.count() == 1


def test_task_form_rejects_kind_without_its_fields(user_client):
    r = user_client.post(reverse("task-add"), {
        "title": "Prune", "schedule_kind": "exact_yearly", "priority": "medium",
        "interval_anchor": "after_completion",
    })
    assert r.status_code == 200
    assert b"Pick the date" in r.content
    assert Task.objects.count() == 0


def test_completing_occurrence_via_view_schedules_next(user_client):
    t = Task.objects.create(title="Mow", schedule_kind=ScheduleKind.EXACT_YEARLY,
                            due_on=datetime.date.today())
    occ = t.create_initial_occurrence()
    r = user_client.post(reverse("occurrence-action", args=[occ.pk, "complete"]))
    assert r.status_code == 302  # no-JS fallback redirects
    occ.refresh_from_db()
    assert occ.status == "completed"
    assert t.occurrences.filter(status="pending").count() == 1


def test_completing_occurrence_htmx_returns_row(user_client):
    t = Task.objects.create(title="Mow", schedule_kind=ScheduleKind.EXACT_ONCE,
                            due_on=datetime.date.today())
    occ = t.create_initial_occurrence()
    r = user_client.post(reverse("occurrence-action", args=[occ.pk, "complete"]),
                         HTTP_HX_REQUEST="true")
    assert r.status_code == 200
    assert b"Done today" in r.content


def test_completed_occurrence_cannot_be_completed_again(user_client):
    t = Task.objects.create(title="Mow", schedule_kind=ScheduleKind.EXACT_ONCE,
                            due_on=datetime.date.today())
    occ = t.create_initial_occurrence()
    occ.complete()
    r = user_client.post(reverse("occurrence-action", args=[occ.pk, "complete"]))
    assert r.status_code == 404  # pending-only lookup guards double completion


# --- Activity / Harvest / Photo / Journal capture ----------------------------


def _png():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buf, "PNG")
    buf.seek(0)
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile("leaf.png", buf.read(), "image/png")


def test_plant_add_with_photo_sets_primary_photo(user_client):
    r = user_client.post(reverse("plant-add"), {
        "common_name": "Lady Fern",
        "planted_precision": "exact",
        "photo": _png(),
    })

    assert r.status_code == 302
    plant = Plant.objects.get(common_name="Lady Fern")
    assert plant.photos.count() == 1
    assert plant.primary_photo == plant.photos.get()


def test_record_activity_lands_in_history(user_client):
    from garden.models import Activity, ActivityType

    plant = Plant.objects.create(common_name="Pear")
    r = user_client.post(reverse("activity-add", args=[plant.pk]), {
        "activity_type": ActivityType.objects.get(name="Pruned").pk,
        "performed_on": datetime.date.today(),
        "note": "took out the crossing branch",
    })
    assert r.status_code == 302
    assert Activity.objects.get().plant == plant
    r = user_client.get(reverse("plant-detail", args=[plant.pk]))
    assert b"Pruned" in r.content and b"crossing branch" in r.content


def test_quick_harvest_and_season_total(user_client):
    from garden.models import HarvestUnit

    plant = Plant.objects.create(common_name="Blueberry", is_edible=True)
    lbs = HarvestUnit.objects.get(name="pounds")
    for qty in ("2.5", "1.5"):
        r = user_client.post(reverse("harvest-add", args=[plant.pk]), {
            "harvested_on": datetime.date.today(), "quantity": qty, "unit": lbs.pk,
        })
        assert r.status_code == 302
    r = user_client.get(reverse("plant-detail", args=[plant.pk]))
    assert b"4 pounds" in r.content  # computed season total, never stored


def test_photo_upload_sets_primary_and_links(user_client):
    plant = Plant.objects.create(common_name="Rose")
    r = user_client.post(reverse("photo-add", args=[plant.pk]),
                         {"file": _png(), "caption": "first bloom"})
    assert r.status_code == 302
    r = user_client.post(reverse("photo-add", args=[plant.pk]),
                         {"file": _png(), "caption": "second bloom"})
    assert r.status_code == 302
    plant.refresh_from_db()
    assert plant.primary_photo is not None
    assert plant.photos.count() == 2
    assert Plant.objects.count() == 1


def test_individual_photo_can_be_removed_without_deleting_plant(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    first = Photo.objects.create(file=_png())
    second = Photo.objects.create(file=_png())
    plant.photos.add(first, second)
    plant.primary_photo = first
    plant.save(update_fields=["primary_photo"])

    response = user_client.post(
        reverse("plant-photo-remove", args=[plant.pk, first.pk])
    )

    assert response.status_code == 302
    plant.refresh_from_db()
    assert Plant.objects.filter(pk=plant.pk).exists()
    assert list(plant.photos.all()) == [second]
    assert plant.primary_photo == second


def test_remove_photo_is_post_only_and_requires_plant_link(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    linked = Photo.objects.create(file=_png())
    unrelated = Photo.objects.create(file=_png())
    plant.photos.add(linked)

    assert user_client.get(
        reverse("plant-photo-remove", args=[plant.pk, linked.pk])
    ).status_code == 405
    assert user_client.post(
        reverse("plant-photo-remove", args=[plant.pk, unrelated.pk])
    ).status_code == 404


def test_plant_photo_can_be_selected_as_primary(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    first = Photo.objects.create(file=_png())
    second = Photo.objects.create(file=_png())
    plant.photos.add(first, second)
    plant.primary_photo = first
    plant.save(update_fields=["primary_photo"])

    response = user_client.post(
        reverse("plant-photo-make-primary", args=[plant.pk, second.pk])
    )

    assert response.status_code == 302
    plant.refresh_from_db()
    assert plant.primary_photo == second
    assert plant.photos.count() == 2


def test_make_primary_photo_is_post_only_and_requires_plant_link(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    linked = Photo.objects.create(file=_png())
    unrelated = Photo.objects.create(file=_png())
    plant.photos.add(linked)
    url = reverse("plant-photo-make-primary", args=[plant.pk, linked.pk])

    assert user_client.get(url).status_code == 405
    assert user_client.post(
        reverse("plant-photo-make-primary", args=[plant.pk, unrelated.pk])
    ).status_code == 404


def test_photo_can_be_moved_to_another_plant_and_repairs_primary_photos(user_client):
    source = Plant.objects.create(common_name="Honeysuckle")
    target = Plant.objects.create(common_name="Climbing Rose")
    moved = Photo.objects.create(file=_png(), caption="Flowers over the arbor")
    remaining = Photo.objects.create(file=_png(), caption="Spring foliage")
    original_name = moved.file.name
    source.photos.add(moved, remaining)
    source.primary_photo = moved
    source.save(update_fields=["primary_photo"])

    response = user_client.post(
        reverse("plant-photo-move", args=[source.pk, moved.pk]),
        {"target_plant": target.pk},
    )

    assert response.status_code == 302
    assert response.url == reverse("plant-photo-detail", args=[target.pk, moved.pk])
    source.refresh_from_db()
    target.refresh_from_db()
    moved.refresh_from_db()
    assert not source.photos.filter(pk=moved.pk).exists()
    assert source.photos.filter(pk=remaining.pk).exists()
    assert source.primary_photo == remaining
    assert target.photos.filter(pk=moved.pk).exists()
    assert target.primary_photo == moved
    assert moved.caption == "Flowers over the arbor"
    assert moved.file.name == original_name


def test_moving_photo_preserves_existing_target_primary(user_client):
    source = Plant.objects.create(common_name="Honeysuckle")
    target = Plant.objects.create(common_name="Climbing Rose")
    moved = Photo.objects.create(file=_png())
    existing_primary = Photo.objects.create(file=_png())
    source.photos.add(moved)
    target.photos.add(existing_primary)
    target.primary_photo = existing_primary
    target.save(update_fields=["primary_photo"])

    response = user_client.post(
        reverse("plant-photo-move", args=[source.pk, moved.pk]),
        {"target_plant": target.pk},
    )

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.primary_photo == existing_primary
    assert target.photos.filter(pk=moved.pk).exists()


def test_move_photo_is_post_only_and_requires_plant_link(user_client):
    source = Plant.objects.create(common_name="Honeysuckle")
    target = Plant.objects.create(common_name="Climbing Rose")
    linked = Photo.objects.create(file=_png())
    unrelated = Photo.objects.create(file=_png())
    source.photos.add(linked)
    url = reverse("plant-photo-move", args=[source.pk, linked.pk])

    assert user_client.get(url).status_code == 405
    assert user_client.post(
        reverse("plant-photo-move", args=[source.pk, unrelated.pk]),
        {"target_plant": target.pk},
    ).status_code == 404


def test_plant_photo_delete_control_has_confirmation(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    photo = Photo.objects.create(file=_png())
    plant.photos.add(photo)

    response = user_client.get(reverse("plant-detail", args=[plant.pk]))

    assert b"Delete photo" in response.content
    assert b"The plant will not be deleted" in response.content


def test_plant_photo_library_marks_primary_and_offers_selection(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    first = Photo.objects.create(file=_png())
    second = Photo.objects.create(file=_png())
    plant.photos.add(first, second)
    plant.primary_photo = first
    plant.save(update_fields=["primary_photo"])

    response = user_client.get(reverse("plant-detail", args=[plant.pk]))

    assert response.content.count(b"Main photo") == 1
    assert response.content.count(b"Make main photo") == 1


def test_plant_photos_offer_lightbox_hover_details_and_context_actions(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    category = PhotoCategory.objects.get(name="Flowers")
    photo = Photo.objects.create(
        file=_png(),
        caption="First fragrant bloom",
        taken_on=datetime.date(2026, 6, 12),
    )
    photo.categories.add(category)
    plant.photos.add(photo)

    response = user_client.get(reverse("plant-detail", args=[plant.pk]))

    assert response.status_code == 200
    assert b"data-photo-lightbox" in response.content
    assert b"js/photo-gallery.js" in response.content
    assert b"First fragrant bloom" in response.content
    assert b"Jun 12, 2026" in response.content
    assert b"Flowers" in response.content
    assert b"Open full information" in response.content
    assert b"Edit photo information" in response.content
    assert b"Zoom in" in response.content


def test_plant_photo_detail_shows_full_information(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    Plant.objects.create(common_name="Climbing Rose")
    category = PhotoCategory.objects.get(name="Whole plant")
    photo = Photo.objects.create(
        file=_png(),
        caption="Vine over the arbor",
        taken_on=datetime.date(2026, 7, 4),
    )
    photo.categories.add(category)
    plant.photos.add(photo)

    response = user_client.get(
        reverse("plant-photo-detail", args=[plant.pk, photo.pk])
    )

    assert response.status_code == 200
    assert b"Photo information" in response.content
    assert b"Vine over the arbor" in response.content
    assert b"July 4, 2026" in response.content
    assert b"Whole plant" in response.content
    assert b"Honeysuckle" in response.content
    assert b"Move to another plant" in response.content
    assert b"Climbing Rose" in response.content
    assert reverse("plant-photo-move", args=[plant.pk, photo.pk]).encode() in response.content


def test_plant_photo_information_can_be_edited_without_replacing_file(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    category = PhotoCategory.objects.get(name="Flowers")
    photo = Photo.objects.create(file=_png(), caption="Old caption")
    original_name = photo.file.name
    plant.photos.add(photo)

    response = user_client.post(
        reverse("plant-photo-edit", args=[plant.pk, photo.pk]),
        {
            "caption": "Pink flowers after rain",
            "taken_on": "2026-08-14",
            "season": "summer",
            "year": "2026",
            "categories": [category.pk],
        },
    )

    assert response.status_code == 302
    photo.refresh_from_db()
    assert photo.caption == "Pink flowers after rain"
    assert photo.taken_on == datetime.date(2026, 8, 14)
    assert photo.season == "summer"
    assert photo.year == 2026
    assert list(photo.categories.all()) == [category]
    assert photo.file.name == original_name
    assert plant.photos.count() == 1


def test_photo_information_pages_require_photo_to_belong_to_plant(user_client):
    plant = Plant.objects.create(common_name="Honeysuckle")
    unrelated = Photo.objects.create(file=_png())

    assert user_client.get(
        reverse("plant-photo-detail", args=[plant.pk, unrelated.pk])
    ).status_code == 404
    assert user_client.get(
        reverse("plant-photo-edit", args=[plant.pk, unrelated.pk])
    ).status_code == 404


def test_additional_photo_page_uses_existing_plant_picker(user_client):
    plant = Plant.objects.create(common_name="Rose")

    r = user_client.get(reverse("photo-add", args=[plant.pk]))

    assert r.status_code == 200
    assert b"It will not create another plant" in r.content
    assert b"Drag another photo here" in r.content
    assert b"choose from Photos or files" in r.content


def test_journal_entry_with_photos_and_plant_link(user_client):
    from garden.models import JournalEntry

    plant = Plant.objects.create(common_name="Fig")
    r = user_client.post(reverse("journal-add"), {
        "text": "First fig of the year, warm off the tree.",
        "plants": [plant.pk],
        "photos_upload": _png(),
    })
    assert r.status_code == 302
    entry = JournalEntry.objects.get()
    assert entry.photos.count() == 1
    assert list(entry.plants.all()) == [plant]
    r = user_client.get(reverse("plant-detail", args=[plant.pk]))
    assert b"First fig" in r.content  # journal shows on the plant profile


def test_journal_search(user_client):
    import django.utils.timezone as tz

    from garden.models import JournalEntry

    JournalEntry.objects.create(occurred_at=tz.now(), text="Aphids on the roses")
    JournalEntry.objects.create(occurred_at=tz.now(), text="Planted garlic")
    r = user_client.get(reverse("journal-list"), {"q": "aphid"})
    assert b"Aphids" in r.content and b"garlic" not in r.content


# --- Proxy-header auth (forward-auth pattern) --------------------------------


def test_proxy_header_auth_creates_user_and_authenticates(client, settings):
    settings.MIDDLEWARE = settings.MIDDLEWARE + [
        "config.auth.AuthentikRemoteUserMiddleware",
    ]
    settings.AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.RemoteUserBackend"]
    r = client.get(reverse("today"), HTTP_X_AUTHENTIK_USERNAME="mekmom")
    assert r.status_code == 200
    assert User.objects.filter(username="mekmom").exists()


def test_no_header_means_no_access(client, settings):
    settings.MIDDLEWARE = settings.MIDDLEWARE + [
        "config.auth.AuthentikRemoteUserMiddleware",
    ]
    settings.AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.RemoteUserBackend"]
    r = client.get(reverse("today"))
    assert r.status_code == 302  # bounced to login, not silently authenticated


def test_health_endpoints_are_public(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


# --- Account section ---------------------------------------------------------


def test_me_page_shows_identity_and_nav_entry(user_client):
    r = user_client.get(reverse("me"))
    assert r.status_code == 200
    assert b"michele" in r.content  # heading + nav user entry


def test_logout_flushes_session(user_client):
    r = user_client.post(reverse("logout"))
    assert r.status_code == 302
    assert user_client.get(reverse("today")).status_code == 302  # back to login


def test_logout_redirect_targets_authentik_end_session_when_proxied(user_client, settings):
    import config.settings as s

    settings.LOGOUT_REDIRECT_URL = s.AUTHENTIK_LOGOUT_URL

    response = user_client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == "https://auth.meklab.net/application/o/yardwise/end-session/"


# --- Settings & beds (#10) ---------------------------------------------------


def test_settings_page_lists_vocab_and_windows(user_client):
    r = user_client.get(reverse("settings"))
    assert r.status_code == 200
    assert b"Late winter" in r.content and b"Pruned" in r.content


def test_vocab_rename_and_builtin_protection(user_client):
    from garden.models import ActivityType

    pruned = ActivityType.objects.get(name="Pruned")
    user_client.post(reverse("settings-vocab", args=["activity-types"]),
                     {"action": "rename", "pk": pruned.pk, "name": "Pruned back"})
    pruned.refresh_from_db()
    assert pruned.name == "Pruned back"
    user_client.post(reverse("settings-vocab", args=["activity-types"]),
                     {"action": "archive", "pk": pruned.pk})
    pruned.refresh_from_db()
    assert pruned.archived_at is None  # builtin: archive refused


def test_vocab_add_and_archive_custom(user_client):
    from garden.models import Tag

    user_client.post(reverse("settings-vocab", args=["tags"]), {"action": "add", "name": "roses"})
    tag = Tag.objects.get(name="roses")
    user_client.post(reverse("settings-vocab", args=["tags"]),
                     {"action": "archive", "pk": tag.pk})
    tag.refresh_from_db()
    assert tag.archived_at is not None


def test_season_window_edit_moves_every_consumer(user_client):
    from garden.models import SeasonWindow

    w = SeasonWindow.objects.get(label="Late winter")
    user_client.post(reverse("settings-window"), {
        "pk": w.pk, "label": "Late winter", "start_month": 2, "start_day": 10,
        "end_month": 3, "end_day": 5,
    })
    w.refresh_from_db()
    assert (w.start_month, w.start_day, w.end_month, w.end_day) == (2, 10, 3, 5)


def test_bed_duplicate_name_rejected_with_prompt(user_client):
    Bed.objects.create(name="Front Bed")
    r = user_client.post(reverse("bed-add"), {"name": "front bed"})
    assert r.status_code == 200
    assert b"pick something distinguishing" in r.content


def test_bed_archive_refused_while_plants_present(user_client):
    bed = Bed.objects.create(name="Front Bed")
    plant = Plant.objects.create(common_name="Rose")
    plant.locations.create(bed=bed, is_current=True)
    user_client.post(reverse("bed-archive", args=[bed.pk]))
    bed.refresh_from_db()
    assert bed.archived_at is None
    plant.locations.update(is_current=False)
    user_client.post(reverse("bed-archive", args=[bed.pk]))
    bed.refresh_from_db()
    assert bed.archived_at is not None


# --- Yard Problems (#22) -----------------------------------------------------


def test_log_problem_from_plant_profile_defaults_to_open_plant(user_client):
    plant = Plant.objects.create(common_name="Rose")

    profile = user_client.get(reverse("plant-detail", args=[plant.pk]))
    response = user_client.get(reverse("problem-add"), {"plant": plant.pk})

    expected_url = reverse("problem-add") + f"?plant={plant.pk}"
    assert expected_url.encode() in profile.content
    assert response.status_code == 200
    assert response.context["form"].initial["plants"] == [plant.pk]
    assert f'<option value="{plant.pk}" selected>Rose</option>'.encode() in response.content


def test_log_problem_offers_multi_photo_drag_and_drop(user_client):
    response = user_client.get(reverse("problem-add"))

    assert response.status_code == 200
    assert b"Drag problem photos here" in response.content
    assert b"choose from Photos or files" in response.content
    assert b"data-photo-picker" in response.content
    assert b"multiple" in response.content
    assert b"js/photo-picker.js" in response.content


def test_log_problem_does_not_preselect_inaccessible_plant(user_client):
    from garden.models import Garden

    other_user = User.objects.create_user("other-problem-owner")
    other_plant = Plant.objects.create(
        garden=Garden.for_user(other_user),
        common_name="Private rose",
    )

    response = user_client.get(reverse("problem-add"), {"plant": other_plant.pk})

    assert response.status_code == 200
    assert "plants" not in response.context["form"].initial
    assert b"Private rose" not in response.content


def test_log_problem_creates_type_and_case(user_client):
    from garden.models import ProblemCase, ProblemType

    plant = Plant.objects.create(common_name="Rose")
    r = user_client.post(reverse("problem-add"), {
        "kind": "pest", "type_name": "Aphids",
        "plants": [plant.pk], "first_observed": datetime.date.today(),
        "severity": "moderate", "confidence": "unknown",
        "follow_up_on": datetime.date.today() + datetime.timedelta(days=7),
    })
    assert r.status_code == 302
    case = ProblemCase.objects.get()
    assert case.problem_type.name == "Aphids" and case.problem_type.kind == "pest"
    # logging the same name reuses the type record (case-insensitive)
    user_client.post(reverse("problem-add"), {
        "kind": "pest", "type_name": "aphids",
        "first_observed": datetime.date.today(),
        "severity": "isolated", "confidence": "unknown",
    })
    assert ProblemType.objects.count() == 1
    assert ProblemCase.objects.count() == 2


def test_log_problem_saves_multiple_photos(user_client):
    from garden.models import ProblemCase

    response = user_client.post(reverse("problem-add"), {
        "kind": "pest",
        "type_name": "Aphids",
        "first_observed": datetime.date.today(),
        "severity": "moderate",
        "confidence": "unknown",
        "photos_upload": [_png(), _png()],
    })

    assert response.status_code == 302
    assert ProblemCase.objects.get().photos.count() == 2


def test_problem_shows_on_plant_profile_and_today(user_client):
    from garden.models import ProblemCase, ProblemType

    plant = Plant.objects.create(common_name="Pear")
    ptype = ProblemType.objects.create(kind="disease", name="Fire blight")
    case = ProblemCase.objects.create(
        problem_type=ptype, first_observed=datetime.date.today(),
        follow_up_on=datetime.date.today(),
    )
    case.plants.add(plant)
    r = user_client.get(reverse("plant-detail", args=[plant.pk]))
    assert b"Fire blight" in r.content and b"Active problems" in r.content
    r = user_client.get(reverse("today"))
    assert b"Problem check-ups" in r.content and b"Fire blight" in r.content


def test_treatment_moves_status_and_resolution_clears_today(user_client):
    from garden.models import ProblemCase, ProblemType

    Plant.objects.create(common_name="Pear")  # Today needs a plant to leave empty-state
    ptype = ProblemType.objects.create(kind="weed", name="Bindweed", seed_alert=True)
    case = ProblemCase.objects.create(
        problem_type=ptype, first_observed=datetime.date.today(),
        follow_up_on=datetime.date.today(),
    )
    r = user_client.post(reverse("treatment-add", args=[case.pk]), {
        "treated_on": datetime.date.today(), "method": "Dug out roots",
        "effectiveness": "unknown",
    })
    assert r.status_code == 302
    case.refresh_from_db()
    assert case.status == "treating"
    # resolve via status button
    user_client.post(reverse("problem-detail", args=[case.pk]), {"status": "resolved"})
    case.refresh_from_db()
    assert case.status == "resolved"
    r = user_client.get(reverse("today"))
    assert b"Problem check-ups" not in r.content  # resolved cases leave Today


def test_problem_list_filters_by_kind(user_client):
    from garden.models import ProblemCase, ProblemType

    weed = ProblemType.objects.create(kind="weed", name="Dandelion")
    pest = ProblemType.objects.create(kind="pest", name="Slugs")
    ProblemCase.objects.create(problem_type=weed, first_observed=datetime.date.today())
    ProblemCase.objects.create(problem_type=pest, first_observed=datetime.date.today())
    r = user_client.get(reverse("problem-list"), {"kind": "weed"})
    assert b"Dandelion" in r.content and b"Slugs" not in r.content


def test_account_page_shows_version(user_client, monkeypatch):
    monkeypatch.setenv("YARDWISE_VERSION", "v9.9.9")
    r = user_client.get(reverse("me"))
    assert b"version v9.9.9" in r.content
