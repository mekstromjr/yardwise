"""Per-user garden isolation: each account sees only its own garden."""

import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden.models import Garden, Notification

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


@pytest.fixture
def alice():
    return User.objects.create_user("alice", password="x")


@pytest.fixture
def bob():
    return User.objects.create_user("bob", password="x")


def _populate(client, user, prefix):
    """Create one bed/plant/task/journal entry through the views (which stamp
    the request user's garden), exactly as a real session would."""
    client.force_login(user)
    client.post(reverse("bed-add"), {"name": f"{prefix} bed"})
    client.post(reverse("plant-add"), {
        "common_name": f"{prefix} plant", "planted_precision": "exact",
        "is_ornamental": "on",
    })
    client.post(reverse("task-add"), {
        "title": f"{prefix} task", "schedule_kind": "exact_once",
        "due_on": TODAY, "priority": "medium", "interval_anchor": "after_completion",
    })
    client.post(reverse("journal-add"), {"text": f"{prefix} journal note"})


def test_for_user_is_idempotent_and_per_user(alice, bob):
    g1 = Garden.for_user(alice)
    assert Garden.for_user(alice).pk == g1.pk
    assert Garden.objects.filter(owner=alice).count() == 1
    assert Garden.for_user(bob).pk != g1.pk


def test_list_pages_and_today_show_only_own_garden(client, alice, bob):
    _populate(client, alice, "alice")
    _populate(client, bob, "bob")

    client.force_login(alice)
    for name, mine, theirs in [
        ("plant-list", b"alice plant", b"bob plant"),
        ("journal-list", b"alice journal note", b"bob journal note"),
        ("bed-list", b"alice bed", b"bob bed"),
        ("today", b"alice task", b"bob task"),
    ]:
        r = client.get(reverse(name))
        assert mine in r.content, name
        assert theirs not in r.content, name
    r = client.get(reverse("task-list"), {"view": "all"})
    assert b"alice task" in r.content and b"bob task" not in r.content


def test_cross_garden_detail_urls_return_404(client, alice, bob):
    _populate(client, alice, "alice")
    from garden.models import Photo, Plant, Task

    plant = Plant.objects.get(common_name="alice plant")
    photo = Photo.objects.create(garden=plant.garden, uploaded_by=alice, file="photo.jpg")
    plant.photos.add(photo)
    occ = Task.objects.get(title="alice task").occurrences.get()

    client.force_login(bob)
    assert client.get(reverse("plant-detail", args=[plant.pk])).status_code == 404
    assert client.post(reverse("plant-archive", args=[plant.pk])).status_code == 404
    assert client.post(reverse("plant-delete", args=[plant.pk])).status_code == 404
    assert client.post(
        reverse("plant-photo-remove", args=[plant.pk, photo.pk])
    ).status_code == 404
    plant.refresh_from_db()
    assert plant.status == "active"
    assert plant.photos.filter(pk=photo.pk).exists()
    assert client.post(
        reverse("occurrence-action", args=[occ.pk, "complete"])
    ).status_code == 404
    # ...while the owner still reaches both.
    client.force_login(alice)
    assert client.get(reverse("plant-detail", args=[plant.pk])).status_code == 200


def test_notifications_do_not_leak_between_gardens(client, alice, bob):
    _populate(client, alice, "alice")  # task due today -> notifiable
    _populate(client, bob, "bob")

    client.force_login(alice)
    r = client.get(reverse("notifications"))  # materializes alice's rows
    assert b"alice task" in r.content and b"bob task" not in r.content
    alice_notif = Notification.objects.get(garden=Garden.for_user(alice))

    client.force_login(bob)
    r = client.get(reverse("notifications"))
    assert b"alice task" not in r.content and b"bob task" in r.content
    # bob cannot act on alice's notification
    assert client.post(
        reverse("notification-action", args=[alice_notif.pk, "dismiss"])
    ).status_code == 404
    alice_notif.refresh_from_db()
    assert alice_notif.dismissed_at is None
