"""Yard Problems: weeds, pests, and diseases (PDD section 7).

One shared framework (PDD canonical rule): a reference record per species or
condition (ProblemType), individual occurrences (ProblemCase), and Treatments.
Category-specific fields live on the shared models and simply stay blank where
they don't apply - the UI shows what fits the kind.
"""

from django.conf import settings
from django.db import models

from .beds import Bed
from .photos import Photo
from .plants import Plant
from .vocab import SeasonWindow


class ProblemKind(models.TextChoices):
    WEED = "weed", "Weed"
    PEST = "pest", "Pest"
    DISEASE = "disease", "Disease / plant health"


class ProblemType(models.Model):
    """Reference record: what this weed/pest/disease IS and how to handle it."""

    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    kind = models.CharField(max_length=7, choices=ProblemKind.choices)
    name = models.CharField(max_length=150)
    scientific_name = models.CharField(max_length=150, blank=True)
    identification_notes = models.TextField(
        blank=True, help_text="Distinguishing features, look-alikes"
    )
    spread_notes = models.TextField(
        blank=True, help_text="How it spreads / life cycle / conditions that favor it"
    )
    control_notes = models.TextField(
        blank=True, help_text="Control or treatment methods, removal and disposal details"
    )
    best_control_window = models.ForeignKey(
        SeasonWindow, null=True, blank=True, on_delete=models.SET_NULL
    )
    # weeds: the "do not let it go to seed" alarm (PDD 7.1)
    seed_alert = models.BooleanField(
        default=False, verbose_name="Do not let it go to seed"
    )
    # pests: beneficial organisms must never be treated by default (PDD 7 IPM)
    is_beneficial = models.BooleanField(default=False)
    photos = models.ManyToManyField(Photo, blank=True, related_name="problem_types")
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["garden", "kind", "name"],
                condition=models.Q(archived_at__isnull=True),
                name="unique_active_problem_type",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"


class Severity(models.TextChoices):
    ISOLATED = "isolated", "Isolated / mild"
    MODERATE = "moderate", "Moderate"
    WIDESPREAD = "widespread", "Widespread / severe"


class CaseStatus(models.TextChoices):
    MONITORING = "monitoring", "Monitoring"
    ACTIVE = "active", "Active"
    TREATING = "treating", "Treating"
    IMPROVING = "improving", "Improving"
    CONTROLLED = "controlled", "Controlled"
    RESOLVED = "resolved", "Resolved"


class Confidence(models.TextChoices):
    """Diagnosis confidence (diseases; PDD: uncertainty is a valid state)."""

    UNKNOWN = "unknown", "Unknown"
    POSSIBLE = "possible", "Possible"
    LIKELY = "likely", "Likely"
    CONFIRMED = "confirmed", "Confirmed"


class ProblemCase(models.Model):
    """A specific occurrence: this weed in that bed, this disease on that plant."""

    problem_type = models.ForeignKey(
        ProblemType, on_delete=models.PROTECT, related_name="cases"
    )
    plants = models.ManyToManyField(Plant, blank=True, related_name="problem_cases")
    bed = models.ForeignKey(
        Bed, null=True, blank=True, on_delete=models.PROTECT, related_name="problem_cases"
    )
    location_note = models.CharField(max_length=200, blank=True)
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    first_observed = models.DateField()
    last_observed = models.DateField(null=True, blank=True)
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.ISOLATED
    )
    status = models.CharField(
        max_length=10, choices=CaseStatus.choices, default=CaseStatus.ACTIVE
    )
    confidence = models.CharField(
        max_length=9, choices=Confidence.choices, default=Confidence.UNKNOWN
    )
    symptoms = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    follow_up_on = models.DateField(
        null=True, blank=True, help_text="Re-inspection date; surfaces on Today"
    )
    photos = models.ManyToManyField(Photo, blank=True, related_name="problem_cases")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-first_observed"]

    def __str__(self):
        return f"{self.problem_type.name} ({self.first_observed})"

    @property
    def is_open(self) -> bool:
        return self.status != CaseStatus.RESOLVED

    @property
    def where(self) -> str:
        if self.bed:
            return self.bed.name + (f" - {self.location_note}" if self.location_note else "")
        return self.location_note or "location not recorded"


class Effectiveness(models.TextChoices):
    UNKNOWN = "unknown", "Too early to tell"
    WORKED = "worked", "Worked"
    PARTIAL = "partial", "Partly worked"
    FAILED = "failed", "Did not work"


class Treatment(models.Model):
    case = models.ForeignKey(ProblemCase, on_delete=models.CASCADE, related_name="treatments")
    treated_on = models.DateField()
    method = models.CharField(
        max_length=200, help_text="Pulled, sprayed neem, pruned out, corrected watering..."
    )
    product = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    effectiveness = models.CharField(
        max_length=7, choices=Effectiveness.choices, default=Effectiveness.UNKNOWN
    )
    photos = models.ManyToManyField(Photo, blank=True, related_name="treatments")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-treated_on"]

    def __str__(self):
        return f"{self.method} ({self.treated_on})"
