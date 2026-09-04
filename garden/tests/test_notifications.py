import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from garden import notify
from garden.models import (
    Notification,
    NotificationKind,
    NotificationPrefs,
    ScheduleKind,
    Task,
)

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


@pytest.fixture
def user():
    return User.objects.create_user("michele", password="x")


@pytest.fixture
def user_client(client, user):
    client.force_login(user)
    return client


def make_occurrence(title="Water the beds", due=TODAY):
    task = Task.objects.create(title=title, schedule_kind=ScheduleKind.EXACT_ONCE, due_on=due)
    return task.create_initial_occurrence()


def test_refresh_is_idempotent_on_double_run():
    make_occurrence(due=TODAY)
    notify.refresh()
    notify.refresh()
    assert Notification.objects.count() == 1
    notif = Notification.objects.get()
    assert notif.kind == NotificationKind.TASK_DUE
    assert notif.dedupe_key.endswith(f"-due-{TODAY.isoformat()}")


def test_overdue_transition_retires_due_notification():
    occ = make_occurrence(due=TODAY)
    notify.refresh()
    due_notif = Notification.objects.get(kind=NotificationKind.TASK_DUE)
    # The due date passes: refresh as of tomorrow materializes the overdue row
    # and marks the superseded due reminder read.
    notify.refresh(today=TODAY + datetime.timedelta(days=1))
    overdue = Notification.objects.get(kind=NotificationKind.TASK_OVERDUE)
    assert overdue.dedupe_key == f"occ-{occ.pk}-overdue"
    due_notif.refresh_from_db()
    assert due_notif.read_at is not None
    # And the overdue row itself dedupes on a third pass.
    notify.refresh(today=TODAY + datetime.timedelta(days=2))
    assert Notification.objects.filter(kind=NotificationKind.TASK_OVERDUE).count() == 1


def test_completing_occurrence_marks_notification_read():
    occ = make_occurrence(due=TODAY)
    notify.refresh()
    notif = Notification.objects.get()
    assert notif.read_at is None
    occ.complete()
    notify.refresh()
    notif.refresh_from_db()
    assert notif.read_at is not None
    assert Notification.visible_unread().count() == 0


def test_snoozed_notification_resurfaces_after_snoozed_until():
    make_occurrence(due=TODAY - datetime.timedelta(days=1))  # overdue: stable across days
    notify.refresh()
    notif = Notification.objects.get(kind=NotificationKind.TASK_OVERDUE)
    notif.snoozed_until = TODAY + datetime.timedelta(days=3)
    notif.save()
    assert notif not in Notification.visible_unread(TODAY)
    # Three days later the snooze has elapsed; refresh clears it.
    later = TODAY + datetime.timedelta(days=3)
    notify.refresh(today=later)
    notif.refresh_from_db()
    assert notif.snoozed_until is None
    assert notif in Notification.visible_unread(later)


def test_prefs_disabled_suppresses_new_notifications(user):
    prefs = NotificationPrefs.for_user(user)
    prefs.enabled = False
    prefs.save()
    make_occurrence(due=TODAY)
    notify.refresh(user=user)
    assert Notification.objects.count() == 0


def test_prefs_lead_days_pull_in_upcoming_tasks(user):
    prefs = NotificationPrefs.for_user(user)
    prefs.lead_days = 3
    prefs.save()
    make_occurrence(title="Prune soon", due=TODAY + datetime.timedelta(days=2))
    make_occurrence(title="Way out", due=TODAY + datetime.timedelta(days=10))
    notify.refresh(user=user)
    titles = set(Notification.objects.values_list("title", flat=True))
    assert titles == {"Prune soon"}
    # Default prefs (lead_days=0) would have produced nothing for either.


def test_default_prefs_are_due_day_only(user):
    make_occurrence(title="Tomorrow job", due=TODAY + datetime.timedelta(days=1))
    notify.refresh(user=user)
    assert Notification.objects.count() == 0


def test_center_renders_and_refreshes(user_client):
    make_occurrence(title="Feed the dahlias", due=TODAY)
    r = user_client.get(reverse("notifications"))
    assert r.status_code == 200
    assert b"Feed the dahlias" in r.content
    assert Notification.objects.count() == 1  # materialized lazily by the visit


def test_dismiss_hides_notification(user_client):
    make_occurrence(due=TODAY)
    notify.refresh()
    notif = Notification.objects.get()
    r = user_client.post(reverse("notification-action", args=[notif.pk, "dismiss"]))
    assert r.status_code == 302
    notif.refresh_from_db()
    assert notif.dismissed_at is not None
    assert Notification.visible_unread().count() == 0
    r = user_client.get(reverse("notifications"))
    assert b"All caught up" in r.content


def test_mark_all_read(user_client):
    make_occurrence(title="One", due=TODAY)
    make_occurrence(title="Two", due=TODAY)
    notify.refresh()
    assert Notification.visible_unread().count() == 2
    user_client.post(reverse("notifications-all-read"))
    assert Notification.visible_unread().count() == 0
    assert Notification.objects.filter(read_at__isnull=False).count() == 2


def test_snooze_action_sets_three_days(user_client):
    make_occurrence(due=TODAY)
    notify.refresh()
    notif = Notification.objects.get()
    user_client.post(reverse("notification-action", args=[notif.pk, "snooze"]))
    notif.refresh_from_db()
    assert notif.snoozed_until == TODAY + datetime.timedelta(days=3)


def test_prefs_form_updates_singleton(user_client, user):
    user_client.post(reverse("notifications-prefs"), {"lead_days": "5"})
    prefs = NotificationPrefs.objects.get(user=user)
    assert prefs.enabled is False  # unchecked checkbox
    assert prefs.lead_days == 5
    user_client.post(reverse("notifications-prefs"), {"enabled": "on", "lead_days": "0"})
    prefs.refresh_from_db()
    assert prefs.enabled is True
    assert NotificationPrefs.objects.count() == 1


def test_badge_context_counts_unread(user_client):
    make_occurrence(title="Badge job", due=TODAY)
    user_client.get(reverse("notifications"))  # materialize
    # Any page rendered with the context processor would carry unread_count;
    # it is not registered in settings yet (integrator step), so call directly.
    from django.test import RequestFactory

    from garden.context_processors import notifications as ctx

    request = RequestFactory().get("/")
    request.user = User.objects.get(username="michele")
    assert ctx(request)["unread_count"] == 1
    Notification.objects.update(read_at=timezone.now())
    assert ctx(request)["unread_count"] == 0
