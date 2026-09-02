"""User-editable vocabulary tables (PDD: "user-controlled vocabulary").

All follow the same shape: a unique name, an is_builtin flag protecting seeded
rows from deletion (they stay renamable), and archive-not-delete semantics.
"""

import datetime

from django.db import models


class VocabularyBase(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_builtin = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlantType(VocabularyBase):
    """Tree, shrub, perennial, annual, vine, bulb, ..."""


class BedType(VocabularyBase):
    """Perennial, vegetable, raised bed, container area, ..."""


class ActivityType(VocabularyBase):
    """Pruned, Fertilized, Watered, Transplanted, ..."""


class TaskCategory(VocabularyBase):
    """Pruning, feeding, cleanup, ..."""


class HarvestUnit(VocabularyBase):
    """fruit, lbs, oz, baskets, cups, bunches, handfuls, ..."""


class PhotoCategory(VocabularyBase):
    """Whole plant, leaves, flowers, fruit, bark, ... (PDD 5.2)."""


class Tag(VocabularyBase):
    """Free-form user labels shared by plants, journal entries, and tasks."""


class SeasonWindow(models.Model):
    """A named horticultural window ("Late winter") mapped to a month/day range.

    Windows may cross the year boundary (Nov 15 - Feb 28). Editing a window's
    range updates every task and plant care field that references it - that is
    the point (PDD Settings: "season definitions/preferences").
    """

    label = models.CharField(max_length=60, unique=True)
    start_month = models.PositiveSmallIntegerField()
    start_day = models.PositiveSmallIntegerField(default=1)
    end_month = models.PositiveSmallIntegerField()
    end_day = models.PositiveSmallIntegerField(default=28)
    is_builtin = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_month", "start_day"]

    def __str__(self):
        return self.label

    @property
    def crosses_year_boundary(self) -> bool:
        return (self.end_month, self.end_day) < (self.start_month, self.start_day)

    def resolve_for_year(self, year: int) -> tuple[datetime.date, datetime.date]:
        """Concrete (start, end) dates for the window instance that STARTS in `year`."""
        start = datetime.date(year, self.start_month, self.start_day)
        end_year = year + 1 if self.crosses_year_boundary else year
        end = datetime.date(end_year, self.end_month, self.end_day)
        return start, end
