"""Vegetable Garden Planner (#24): the two-level annual-crop model.

A permanent Variety record stores reusable crop facts (PDD 6.1); each year's
grow is a SeasonalPlanting. Milestone dates are COMPUTED from the variety's
frost-relative offsets plus the property ClimateProfile - never stored - so
editing the climate profile or a variety's timing reflows every plan (PDD 6.6).
Method-appropriate milestones only (PDD 6.10): a purchase-starts planting never
nags about seed trays.

Uncertainty is a valid state throughout: every timing field is nullable and a
milestone whose inputs are missing is simply omitted, never guessed.
"""

import datetime

from django.conf import settings
from django.db import models

from .beds import Bed

ROTATION_YEARS = 3  # warn when the same crop family repeats in a bed within this many prior years


class CropFamily(models.TextChoices):
    NIGHTSHADE = "nightshade", "Nightshade"
    BRASSICA = "brassica", "Brassica"
    LEGUME = "legume", "Legume"
    CUCURBIT = "cucurbit", "Cucurbit"
    ALLIUM = "allium", "Allium"
    ROOT = "root", "Root crop"
    LEAFY = "leafy", "Leafy green"
    HERB = "herb", "Herb"
    OTHER = "other", "Other"


class Variety(models.Model):
    """Permanent crop/cultivar record, reused year after year (PDD 6.1).

    Timing fields are offsets in whole weeks relative to the average last
    spring frost ("LF"). Negative `direct_sow_weeks` means before last frost
    (peas); all offsets are nullable because seed packets disagree and the
    user may simply not know yet.
    """

    name = models.CharField(max_length=100)
    botanical_name = models.CharField(max_length=150, blank=True)
    cultivar = models.CharField(max_length=100, blank=True)
    crop_family = models.CharField(
        max_length=10, choices=CropFamily.choices, blank=True
    )  # blank = unknown: no fake default, and no rotation warnings until the user says
    days_to_maturity = models.PositiveSmallIntegerField(null=True, blank=True)
    spacing_notes = models.CharField(max_length=200, blank=True)
    start_indoors_weeks_before_lf = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="start indoors (weeks before last frost)"
    )
    transplant_weeks_after_lf = models.SmallIntegerField(
        null=True, blank=True, verbose_name="transplant outdoors (weeks after last frost)"
    )
    direct_sow_weeks = models.SmallIntegerField(
        null=True, blank=True,
        verbose_name="direct sow (weeks after last frost, negative = before)",
    )
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "cultivar"]
        verbose_name_plural = "varieties"

    def __str__(self):
        return f"{self.name} '{self.cultivar}'" if self.cultivar else self.name


class ClimateProfile(models.Model):
    """The property climate profile (PDD 6.5) - one shared row, user-edited.

    Frost dates are stored as month/day (they recur yearly); helpers resolve
    them to concrete dates for a growing year. All fields nullable: an unset
    profile means the planner shows plans without computed dates rather than
    inventing them.
    """

    hardiness_zone = models.CharField(max_length=10, blank=True)
    avg_last_frost_month = models.PositiveSmallIntegerField(null=True, blank=True)
    avg_last_frost_day = models.PositiveSmallIntegerField(null=True, blank=True)
    avg_first_frost_month = models.PositiveSmallIntegerField(null=True, blank=True)
    avg_first_frost_day = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Climate profile (zone {self.hardiness_zone or 'unset'})"

    @classmethod
    def load(cls) -> "ClimateProfile":
        profile, _created = cls.objects.get_or_create(pk=1)
        return profile

    def last_frost_date(self, year: int) -> datetime.date | None:
        if not (self.avg_last_frost_month and self.avg_last_frost_day):
            return None
        return datetime.date(year, self.avg_last_frost_month, self.avg_last_frost_day)

    def first_frost_date(self, year: int) -> datetime.date | None:
        if not (self.avg_first_frost_month and self.avg_first_frost_day):
            return None
        return datetime.date(year, self.avg_first_frost_month, self.avg_first_frost_day)


class PlantingStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    STARTED_INDOORS = "started_indoors", "Started indoors"
    HARDENING = "hardening", "Hardening off"
    PLANTED = "planted", "Planted"
    FINISHED = "finished", "Finished"


class GrowingMethod(models.TextChoices):
    SEED_INDOORS = "seed_indoors", "Start seeds indoors"
    DIRECT_SOW = "direct_sow", "Direct sow"
    PURCHASE_STARTS = "purchase_starts", "Purchase starts"
    UNDECIDED = "undecided", "Undecided"


class GrowAgain(models.TextChoices):
    YES = "yes", "Yes"
    NO = "no", "No"
    MAYBE = "maybe", "Maybe"


class SeasonalPlanting(models.Model):
    """One variety grown (or planned) in one year (PDD 6.1/6.2).

    Closing a season never touches the Variety; the permanent record stays
    available for next year and history rows are kept for comparison.
    """

    variety = models.ForeignKey(Variety, on_delete=models.PROTECT, related_name="plantings")
    year = models.PositiveSmallIntegerField()
    bed = models.ForeignKey(
        Bed, null=True, blank=True, on_delete=models.PROTECT, related_name="plantings"
    )  # nullable = "planned, no bed chosen yet" - progressive entry
    status = models.CharField(
        max_length=15, choices=PlantingStatus.choices, default=PlantingStatus.PLANNED
    )
    growing_method = models.CharField(
        max_length=15, choices=GrowingMethod.choices, default=GrowingMethod.UNDECIDED
    )
    planned_quantity = models.PositiveSmallIntegerField(null=True, blank=True)
    sowed_on = models.DateField(null=True, blank=True)
    transplanted_on = models.DateField(null=True, blank=True)
    first_harvest_on = models.DateField(null=True, blank=True)
    last_harvest_on = models.DateField(null=True, blank=True)
    grow_again = models.CharField(max_length=5, choices=GrowAgain.choices, blank=True)
    season_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "variety__name"]

    def __str__(self):
        return f"{self.variety} - {self.year}"

    # --- Milestone schedule (PDD 6.6, 6.10) ---------------------------------

    @property
    def milestones(self) -> list[tuple[str, datetime.date]]:
        """Method-appropriate (label, date) milestones, computed on the fly.

        Anything whose inputs are missing (no climate profile, no offset on
        the variety) is omitted - an honest partial schedule beats a fake one.
        """
        return self.compute_milestones(ClimateProfile.load())

    def compute_milestones(self, climate: ClimateProfile) -> list[tuple[str, datetime.date]]:
        lf = climate.last_frost_date(self.year)
        if lf is None:
            return []
        v = self.variety
        week = datetime.timedelta(weeks=1)
        out: list[tuple[str, datetime.date]] = []

        start_indoors = (
            lf - v.start_indoors_weeks_before_lf * week
            if v.start_indoors_weeks_before_lf is not None else None
        )
        transplant = (
            lf + v.transplant_weeks_after_lf * week
            if v.transplant_weeks_after_lf is not None else None
        )
        direct_sow = (
            lf + v.direct_sow_weeks * week if v.direct_sow_weeks is not None else None
        )

        method = self.growing_method
        planted_estimate = None  # the computed in-ground date, for the harvest estimate
        if method == GrowingMethod.SEED_INDOORS:
            if start_indoors:
                out.append(("Start seeds indoors", start_indoors))
            if transplant:
                out.append(("Transplant outdoors", transplant))
                planted_estimate = transplant
        elif method == GrowingMethod.DIRECT_SOW:
            if direct_sow:
                out.append(("Direct sow", direct_sow))
                planted_estimate = direct_sow
        elif method == GrowingMethod.PURCHASE_STARTS:
            if transplant:
                out.append(("Buy and plant starts", transplant))
                planted_estimate = transplant
        else:  # undecided: surface both timelines so the user can choose (PDD 6.10)
            if start_indoors:
                out.append(("If starting indoors: start seeds", start_indoors))
            if direct_sow:
                out.append(("If direct sowing: sow", direct_sow))

        # Expected first harvest: actual in-ground date wins over the estimate.
        in_ground = self.sowed_on or self.transplanted_on or planted_estimate
        if v.days_to_maturity and in_ground:
            out.append(
                ("Expected first harvest", in_ground + datetime.timedelta(days=v.days_to_maturity))
            )
        out.sort(key=lambda item: item[1])
        return out

    # --- Crop rotation (PDD 6.3) --------------------------------------------

    def rotation_conflicts(self):
        """Prior plantings of the same crop family in this bed within the last
        ROTATION_YEARS years. Advisory only - the user may override (PDD 6.3).
        """
        family = self.variety.crop_family
        if not (self.bed_id and family):
            return SeasonalPlanting.objects.none()
        return (
            SeasonalPlanting.objects.filter(
                bed_id=self.bed_id,
                variety__crop_family=family,
                year__gte=self.year - ROTATION_YEARS,
                year__lt=self.year,
                archived_at__isnull=True,
            )
            .exclude(pk=self.pk)
            .select_related("variety")
        )
