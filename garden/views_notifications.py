"""Notification center (#26): lazy refresh + read/snooze/dismiss + prefs.

No background jobs - notify.refresh() runs on every center visit and is
idempotent, so the list is always current the moment it is looked at.
"""

import datetime
import itertools

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import notify
from .models import Notification, NotificationPrefs

SNOOZE_DAYS = 3
RECENT_READ_LIMIT = 20


def _day_groups(notifications):
    """[(day label, [notifications])] grouped by local created date, newest first."""
    def day(n):
        return timezone.localtime(n.created_at).date()

    groups = []
    for d, items in itertools.groupby(notifications, key=day):
        today = datetime.date.today()
        if d == today:
            label = "Today"
        elif d == today - datetime.timedelta(days=1):
            label = "Yesterday"
        else:
            label = d.strftime("%B %-d")
        groups.append((label, list(items)))
    return groups


@login_required
def center(request):
    notify.refresh(user=request.user)
    today = datetime.date.today()
    unread = list(Notification.visible_unread(today))
    recent_read = list(
        Notification.objects.filter(dismissed_at__isnull=True, read_at__isnull=False)[
            :RECENT_READ_LIMIT
        ]
    )
    return render(request, "garden/notifications/center.html", {
        "nav": "me",
        "unread_groups": _day_groups(unread),
        "read_groups": _day_groups(recent_read),
        "unread_total": len(unread),
        "prefs": NotificationPrefs.for_user(request.user),
    })


@login_required
def action(request, pk, action):
    if request.method != "POST":
        return redirect("notifications")
    notif = get_object_or_404(Notification, pk=pk)
    if action == "read":
        notif.read_at = notif.read_at or timezone.now()
        notif.save(update_fields=["read_at"])
    elif action == "snooze":
        notif.snoozed_until = datetime.date.today() + datetime.timedelta(days=SNOOZE_DAYS)
        notif.save(update_fields=["snoozed_until"])
    elif action == "dismiss":
        notif.dismissed_at = notif.dismissed_at or timezone.now()
        notif.save(update_fields=["dismissed_at"])
    return redirect("notifications")


@login_required
def mark_all_read(request):
    if request.method == "POST":
        Notification.visible_unread().update(read_at=timezone.now())
    return redirect("notifications")


@login_required
def prefs_update(request):
    if request.method == "POST":
        prefs = NotificationPrefs.for_user(request.user)
        prefs.enabled = request.POST.get("enabled") == "on"
        raw = request.POST.get("lead_days", "0")
        if raw.isdigit():
            prefs.lead_days = min(30, int(raw))
        prefs.save()
    return redirect("notifications")
