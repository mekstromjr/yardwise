"""Activities, journal entries, and harvest events - the durable history."""

from django.conf import settings
from django.db import models

from .beds import Bed
from .photos import Photo
from .plants import Plant
from .vocab import ActivityType, HarvestUnit, Tag


class Activity(models.Model):
    """A completed piece of garden work, plant- or bed-scoped (at least one)."""

    plant = models.ForeignKey(
        Plant, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    bed = models.ForeignKey(
        Bed, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    activity_type = models.ForeignKey(ActivityType, on_delete=models.PROTECT)
    performed_on = models.DateField()
    note = models.TextField(blank=True)
    photos = models.ManyToManyField(Photo, blank=True, related_name="activities")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_on"]
        verbose_name_plural = "activities"
        constraints = [
            models.CheckConstraint(
                name="activity_has_plant_or_bed",
                condition=models.Q(plant__isnull=False) | models.Q(bed__isnull=False),
            ),
        ]

    def __str__(self):
        target = self.plant or self.bed
        return f"{self.activity_type} - {target} ({self.performed_on})"


class JournalEntry(models.Model):
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    occurred_at = models.DateTimeField()
    text = models.TextField()
    photos = models.ManyToManyField(Photo, blank=True, related_name="journal_entries")
    plants = models.ManyToManyField(Plant, blank=True, related_name="journal_entries")
    beds = models.ManyToManyField(Bed, blank=True, related_name="journal_entries")
    tags = models.ManyToManyField(Tag, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name_plural = "journal entries"

    def __str__(self):
        return f"Journal {self.occurred_at:%Y-%m-%d}"


class HarvestQuality(models.TextChoices):
    POOR = "poor", "Poor"
    FAIR = "fair", "Fair"
    GOOD = "good", "Good"
    EXCELLENT = "excellent", "Excellent"


class HarvestEvent(models.Model):
    """One harvest from one plant. Only the date is required (R-093).

    Season totals are computed queries grouped by year and unit - never stored,
    so corrections can't desync a rollup.
    """

    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="harvests")
    seasonal_planting = models.ForeignKey(
        "garden.SeasonalPlanting",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="harvests",
    )  # PDD 6.12: harvests link to the specific seasonal planting, not only the variety
    harvested_on = models.DateField()
    quantity = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    unit = models.ForeignKey(HarvestUnit, null=True, blank=True, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(null=True, blank=True)  # optional count alongside weight
    quality = models.CharField(max_length=9, choices=HarvestQuality.choices, blank=True)
    intended_use = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    photos = models.ManyToManyField(Photo, blank=True, related_name="harvests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-harvested_on"]

    def __str__(self):
        return f"{self.plant.common_name} harvest {self.harvested_on}"
