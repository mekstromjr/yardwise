"""Plants (specimens) and their placements.

Identity/care fields grouped at the top of Plant are future Variety-extraction
candidates (Garden Planner module); specimen fields follow. Placement lives in
PlantLocation, its own table, per the identity-vs-placement canonical rule.
"""

from django.conf import settings
from django.db import models

from .photos import Photo
from .vocab import PlantType, SeasonWindow, Tag


class DatePrecision(models.TextChoices):
    EXACT = "exact", "Exact date"
    MONTH = "month", "Month known"
    YEAR = "year", "Year known"


class SunNeeds(models.TextChoices):
    FULL = "full", "Full sun"
    PART = "part", "Part sun/shade"
    SHADE = "shade", "Shade"


class WaterNeeds(models.TextChoices):
    LOW = "low", "Low"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"


class Foliage(models.TextChoices):
    EVERGREEN = "evergreen", "Evergreen"
    DECIDUOUS = "deciduous", "Deciduous"
    SEMI = "semi", "Semi-evergreen"


class PlantStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    REMOVED = "removed", "Removed"
    DIED = "died", "Died"


class Plant(models.Model):
    # --- identity & care (future Variety candidates; all optional but the name) ---
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    common_name = models.CharField(max_length=200)  # the ONLY required field (AC-124)
    botanical_name = models.CharField(max_length=200, blank=True)
    cultivar = models.CharField(max_length=200, blank=True)
    plant_type = models.ForeignKey(PlantType, null=True, blank=True, on_delete=models.PROTECT)
    is_edible = models.BooleanField(default=False)
    is_ornamental = models.BooleanField(default=True)
    foliage = models.CharField(max_length=10, choices=Foliage.choices, blank=True)
    sun = models.CharField(max_length=6, choices=SunNeeds.choices, blank=True)
    water_needs = models.CharField(max_length=8, choices=WaterNeeds.choices, blank=True)
    soil_notes = models.TextField(blank=True)
    mature_height = models.CharField(max_length=60, blank=True)  # "6-8 ft" beats fake precision
    mature_width = models.CharField(max_length=60, blank=True)
    bloom_window = models.ForeignKey(
        SeasonWindow, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    harvest_window = models.ForeignKey(
        SeasonWindow, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    prune_window = models.ForeignKey(
        SeasonWindow, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    fertilize_window = models.ForeignKey(
        SeasonWindow, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    toxicity_notes = models.TextField(blank=True)

    # --- specimen ---
    planted_on = models.DateField(null=True, blank=True)
    planted_precision = models.CharField(
        max_length=5, choices=DatePrecision.choices, default=DatePrecision.EXACT
    )
    source = models.CharField(max_length=200, blank=True)  # nursery, gift, cutting...
    status = models.CharField(
        max_length=8, choices=PlantStatus.choices, default=PlantStatus.ACTIVE
    )
    notes = models.TextField(blank=True)
    primary_photo = models.ForeignKey(
        Photo, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    is_favorite = models.BooleanField(default=False)
    watch_reason = models.CharField(max_length=200, blank=True)  # non-blank = watched
    tags = models.ManyToManyField(Tag, blank=True)
    photos = models.ManyToManyField(Photo, blank=True, related_name="plants")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["common_name"]

    def __str__(self):
        return f"{self.common_name} '{self.cultivar}'" if self.cultivar else self.common_name

    @property
    def is_watched(self) -> bool:
        return bool(self.watch_reason)

    @property
    def current_locations(self):
        return self.locations.filter(is_current=True)


class PlantLocation(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="locations")
    bed = models.ForeignKey(
        "garden.Bed",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="plant_locations",
    )
    location_note = models.CharField(max_length=200, blank=True)  # "north edge, fence side"
    # Exact map point (map module), map units; null = bed-level only.
    point_x = models.FloatField(null=True, blank=True)
    point_y = models.FloatField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=True)
    started_on = models.DateField(null=True, blank=True)
    ended_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-is_current", "-started_on"]

    def __str__(self):
        where = self.bed.name if self.bed else "unassigned"
        return f"{self.plant} @ {where}"
