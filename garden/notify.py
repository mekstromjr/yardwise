"""The notification engine (PDD section 10). No scheduler, no cron.

refresh() is a pure-ish materializer called at request time from the
notification center (cheap enough to run on every visit):

- pending TaskOccurrences due today (or within the user's lead_days) get one
  ``task_due`` notification per occurrence per due date;
- overdue occurrences get one ``task_overdue`` notification per occurrence,
  and any unread ``task_due`` row for the same occurrence is retired;
- notifications whose occurrence is no longer pending (completed/skipped/
  deleted) are marked read so completing work never leaves stale unread rows;
- snoozes that have elapsed are cleared so those rows resurface;
- ProblemCase follow-ups are generated only if that model exists on this
  branch (guarded import).

Idempotency comes from get_or_create on the unique dedupe_key.
"""

import datetime

from django.urls import reverse
from django.utils import timezone

from .models import (
    Notification,
    NotificationKind,
    NotificationPrefs,
    OccurrenceStatus,
    TaskOccurrence,
)

OCC_PREFIX = "occ-"


def refresh(user=None, today: datetime.date | None = None) -> None:
    today = today or datetime.date.today()
    enabled, lead_days = _prefs(user)

    pending = TaskOccurrence.objects.filter(
        status=OccurrenceStatus.PENDING, task__archived_at__isnull=True
    ).select_related("task")

    pending_ids = set()
    for occ in pending:
        pending_ids.add(occ.pk)
        if enabled:
            _materialize_for_occurrence(occ, user, today, lead_days)

    _retire_stale(pending_ids)
    # Elapsed snoozes resurface: clearing the date returns rows to the unread set.
    Notification.objects.filter(snoozed_until__lte=today).update(snoozed_until=None)
    if enabled:
        _materialize_problem_followups(user, today)


def _prefs(user) -> tuple[bool, int]:
    if user is None or not getattr(user, "is_authenticated", False):
        return True, 0
    prefs = NotificationPrefs.for_user(user)
    return prefs.enabled, prefs.lead_days


def _materialize_for_occurrence(occ, user, today, lead_days) -> None:
    due = occ.effective_due  # exact due date, or the window's end
    if due is None:
        return
    link = reverse("task-list") + f"#occ-{occ.pk}"
    if due < today:
        _, created = Notification.objects.get_or_create(
            dedupe_key=f"{OCC_PREFIX}{occ.pk}-overdue",
            defaults={
                "kind": NotificationKind.TASK_OVERDUE,
                "title": occ.task.title,
                "body": f"Overdue since {due:%b %-d}",
                "link_path": link,
                "user": user if user and user.is_authenticated else None,
            },
        )
        if created:  # the due reminder is superseded, not left dangling
            Notification.objects.filter(
                dedupe_key__startswith=f"{OCC_PREFIX}{occ.pk}-due-", read_at__isnull=True
            ).update(read_at=timezone.now())
    elif occ.is_due_now(today) or due <= today + datetime.timedelta(days=lead_days):
        Notification.objects.get_or_create(
            dedupe_key=f"{OCC_PREFIX}{occ.pk}-due-{due.isoformat()}",
            defaults={
                "kind": NotificationKind.TASK_DUE,
                "title": occ.task.title,
                "body": f"Due {due:%b %-d}" if due != today else "Due today",
                "link_path": link,
                "user": user if user and user.is_authenticated else None,
            },
        )


def _retire_stale(pending_ids: set[int]) -> None:
    """Mark occurrence-backed notifications read once their occurrence is done."""
    now = timezone.now()
    stale = []
    for notif in Notification.objects.filter(
        read_at__isnull=True, dedupe_key__startswith=OCC_PREFIX
    ).only("id", "dedupe_key"):
        try:
            occ_id = int(notif.dedupe_key.split("-")[1])
        except (IndexError, ValueError):
            continue
        if occ_id not in pending_ids:
            stale.append(notif.id)
    if stale:
        Notification.objects.filter(id__in=stale).update(read_at=now)


def _materialize_problem_followups(user, today) -> None:
    """ProblemCase is a later module; generate follow-ups only if it exists."""
    try:
        from .models import ProblemCase  # noqa: F401
    except ImportError:
        return
    for case in ProblemCase.objects.exclude(status="resolved").filter(
        follow_up_on__isnull=False, follow_up_on__lte=today
    ).select_related("problem_type"):
        Notification.objects.get_or_create(
            dedupe_key=f"problem-{case.pk}-followup-{case.follow_up_on.isoformat()}",
            defaults={
                "kind": NotificationKind.PROBLEM_FOLLOWUP,
                "title": f"Check on {case.problem_type.name}",
                "body": case.where,
                "link_path": f"/problems/{case.pk}/",
                "user": user if user and user.is_authenticated else None,
            },
        )
