"""Notifications: in-app delivery of notifiable moments (PDD section 10).

Canonical rules: tasks are the durable records; a Notification is only the
DELIVERY of one. Notifications are opt-in (NotificationPrefs.enabled),
deduplicated against completed actions via a unique dedupe_key, and support
read / snooze / dismiss. No background jobs: rows are materialized lazily by
garden.notify.refresh() at request time.

The nullable user FK exists for future per-person delivery (web push, etc.);
today the household shares one garden and rows are created unassigned.
"""

import datetime

from django.conf import settings
from django.db import models


class NotificationKind(models.TextChoices):
    TASK_DUE = "task_due", "Task due"
    TASK_OVERDUE = "task_overdue", "Task overdue"
    PROBLEM_FOLLOWUP = "problem_followup", "Problem follow-up"
    SEASONAL = "seasonal", "Seasonal"


class Notification(models.Model):
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    kind = models.CharField(max_length=16, choices=NotificationKind.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=300, blank=True)
    link_path = models.CharField(max_length=300, blank=True)  # relative URL into the app
    dedupe_key = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(  # nullable: future per-person delivery
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
        related_name="notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    snoozed_until = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind}: {self.title}"

    @property
    def is_unread(self) -> bool:
        return self.read_at is None and self.dismissed_at is None

    @classmethod
    def visible_unread(cls, today: datetime.date | None = None, garden=None):
        """Unread, not dismissed, not currently snoozed. Pass ``garden`` to
        scope to one garden's rows (views always do); ``None`` is unscoped."""
        today = today or datetime.date.today()
        qs = cls.objects.filter(read_at__isnull=True, dismissed_at__isnull=True).filter(
            models.Q(snoozed_until__isnull=True) | models.Q(snoozed_until__lte=today)
        )
        if garden is not None:
            qs = qs.filter(garden=garden)
        return qs


class NotificationPrefs(models.Model):
    """Singleton-per-user preferences (get_or_create via for_user)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_prefs"
    )
    enabled = models.BooleanField(default=True)
    # 0 = notify on the due day only; N = also surface tasks due within N days.
    lead_days = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "notification prefs"

    def __str__(self):
        return f"prefs for {self.user}"

    @classmethod
    def for_user(cls, user) -> "NotificationPrefs":
        prefs, _ = cls.objects.get_or_create(user=user)
        return prefs
