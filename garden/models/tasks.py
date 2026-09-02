"""Tasks: durable definitions + materialized occurrences (schema.md).

Lifecycle rules (no scheduler, no background jobs):
- creating a Task materializes its first TaskOccurrence
- completing/skipping an occurrence synchronously creates the next one for
  recurring kinds; the completed row is history and is never modified again
"""

import datetime

from django.conf import settings
from django.db import models

from .beds import Bed
from .plants import Plant
from .vocab import SeasonWindow, Tag, TaskCategory


class ScheduleKind(models.TextChoices):
    """The five valid timing shapes - not a matrix of independent flags."""

    EXACT_ONCE = "exact_once", "On a date"
    EXACT_YEARLY = "exact_yearly", "Same date every year"
    WINDOW_ONCE = "window_once", "Once, within a seasonal window"
    WINDOW_YEARLY = "window_yearly", "Every year, within a seasonal window"
    INTERVAL = "interval", "Repeating every N days/weeks/months"


class IntervalUnit(models.TextChoices):
    DAYS = "days", "Days"
    WEEKS = "weeks", "Weeks"
    MONTHS = "months", "Months"


class IntervalAnchor(models.TextChoices):
    AFTER_COMPLETION = "after_completion", "After each completion"
    FIXED = "fixed", "From a fixed date"


class Priority(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class Task(models.Model):
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    category = models.ForeignKey(TaskCategory, null=True, blank=True, on_delete=models.PROTECT)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.MEDIUM)

    # Applies to any combination of plants, beds, and/or a tag. A tag target is
    # resolved to plants at display time, not frozen at creation.
    plants = models.ManyToManyField(Plant, blank=True, related_name="tasks")
    beds = models.ManyToManyField(Bed, blank=True, related_name="tasks")
    tag = models.ForeignKey(Tag, null=True, blank=True, on_delete=models.SET_NULL)

    schedule_kind = models.CharField(max_length=14, choices=ScheduleKind.choices)
    due_on = models.DateField(null=True, blank=True)  # EXACT_* kinds
    window = models.ForeignKey(
        SeasonWindow, null=True, blank=True, on_delete=models.PROTECT
    )  # WINDOW_* kinds
    interval_count = models.PositiveSmallIntegerField(null=True, blank=True)  # INTERVAL
    interval_unit = models.CharField(
        max_length=6, choices=IntervalUnit.choices, blank=True
    )
    interval_anchor = models.CharField(
        max_length=16, choices=IntervalAnchor.choices, default=IntervalAnchor.AFTER_COMPLETION
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.CheckConstraint(
                name="task_timing_fields_match_kind",
                condition=(
                    models.Q(schedule_kind__in=["exact_once", "exact_yearly"], due_on__isnull=False)
                    | models.Q(
                        schedule_kind__in=["window_once", "window_yearly"], window__isnull=False
                    )
                    | models.Q(schedule_kind="interval", interval_count__isnull=False)
                ),
            ),
        ]

    def __str__(self):
        return self.title

    # --- occurrence generation -------------------------------------------------

    def create_initial_occurrence(self) -> "TaskOccurrence":
        today = datetime.date.today()
        if self.schedule_kind in (ScheduleKind.EXACT_ONCE, ScheduleKind.EXACT_YEARLY):
            return self.occurrences.create(due_on=self.due_on)
        if self.schedule_kind in (ScheduleKind.WINDOW_ONCE, ScheduleKind.WINDOW_YEARLY):
            start, end = self.window.resolve_for_year(today.year)
            if end < today:  # this year's window already passed; schedule next year's
                start, end = self.window.resolve_for_year(today.year + 1)
            return self.occurrences.create(window_start=start, window_end=end)
        # INTERVAL: first occurrence lands one interval from the anchor (or today).
        anchored = self.interval_anchor == IntervalAnchor.FIXED and self.due_on
        base = self.due_on if anchored else today
        return self.occurrences.create(due_on=_add_interval(base, self))

    def create_next_occurrence(self, completed: "TaskOccurrence") -> "TaskOccurrence | None":
        """Called when an occurrence is completed or skipped. Returns None for one-shot kinds."""
        if self.archived_at:
            return None
        if self.schedule_kind == ScheduleKind.EXACT_YEARLY:
            nxt = _shift_year(completed.due_on)
            return self.occurrences.create(due_on=nxt)
        if self.schedule_kind == ScheduleKind.WINDOW_YEARLY:
            start, end = self.window.resolve_for_year(completed.window_start.year + 1)
            return self.occurrences.create(window_start=start, window_end=end)
        if self.schedule_kind == ScheduleKind.INTERVAL:
            if self.interval_anchor == IntervalAnchor.AFTER_COMPLETION:
                base = completed.completed_on or datetime.date.today()
            else:
                base = completed.due_on
            return self.occurrences.create(due_on=_add_interval(base, self))
        return None  # EXACT_ONCE / WINDOW_ONCE


class OccurrenceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    SKIPPED = "skipped", "Skipped"


class TaskOccurrence(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="occurrences")
    due_on = models.DateField(null=True, blank=True)
    window_start = models.DateField(null=True, blank=True)
    window_end = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=9, choices=OccurrenceStatus.choices, default=OccurrenceStatus.PENDING
    )
    completed_on = models.DateField(null=True, blank=True)
    completion_note = models.TextField(blank=True)
    activity = models.ForeignKey(
        "garden.Activity", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_on", "window_start"]

    def __str__(self):
        return f"{self.task.title} ({self.status})"

    @property
    def effective_due(self) -> datetime.date | None:
        """Sort/overdue key: exact due date, or the window's end."""
        return self.due_on or self.window_end

    def is_overdue(self, today: datetime.date | None = None) -> bool:
        today = today or datetime.date.today()
        due = self.effective_due
        return self.status == OccurrenceStatus.PENDING and due is not None and due < today

    def is_due_now(self, today: datetime.date | None = None) -> bool:
        today = today or datetime.date.today()
        if self.status != OccurrenceStatus.PENDING:
            return False
        if self.due_on:
            return self.due_on <= today
        return self.window_start <= today <= self.window_end

    def complete(self, on=None, note="", activity=None) -> "TaskOccurrence | None":
        """Complete this occurrence; returns the next occurrence for recurring tasks."""
        self.status = OccurrenceStatus.COMPLETED
        self.completed_on = on or datetime.date.today()
        self.completion_note = note
        self.activity = activity
        self.save()
        return self.task.create_next_occurrence(self)

    def skip(self) -> "TaskOccurrence | None":
        """"Not this year" - preserved in history, next occurrence still scheduled."""
        self.status = OccurrenceStatus.SKIPPED
        self.completed_on = datetime.date.today()
        self.save()
        return self.task.create_next_occurrence(self)


def _add_interval(base: datetime.date, task: Task) -> datetime.date:
    if task.interval_unit == IntervalUnit.DAYS:
        return base + datetime.timedelta(days=task.interval_count)
    if task.interval_unit == IntervalUnit.WEEKS:
        return base + datetime.timedelta(weeks=task.interval_count)
    # months: clamp the day to the target month's length (Jan 31 + 1mo -> Feb 28/29)
    month_index = base.month - 1 + task.interval_count
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, _days_in_month(year, month))
    return datetime.date(year, month, day)


def _shift_year(d: datetime.date) -> datetime.date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + 1, day=28)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day
