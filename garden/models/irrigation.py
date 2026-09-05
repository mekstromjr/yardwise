"""Irrigation: zones, components, and the shared event history.

The sprinkler system is reverse-engineered over time (PDD 8), so Unknown is a
first-class value everywhere: a zone can exist before anyone knows what it
waters, a component can exist before its zone is known, and records move from
Unknown toward Verified as evidence accumulates. Never coerce an unknown.

Map geometry is out of scope here - the Property Map module adds it later.
Locations are bed links plus free-text notes.
"""

from django.conf import settings
from django.db import models, transaction

from .beds import Bed
from .photos import Photo


class ZoneType(models.TextChoices):
    SPRAY = "spray", "Spray"
    ROTOR = "rotor", "Rotor"
    DRIP = "drip", "Drip"
    BUBBLER = "bubbler", "Bubbler"
    MANUAL = "manual", "Hose / manual"
    MIXED = "mixed", "Mixed"
    UNKNOWN = "unknown", "Unknown"


class InvestigationStatus(models.TextChoices):
    """How well-understood a zone is. Unknown is the honest default."""

    UNKNOWN = "unknown", "Unknown"
    PARTIALLY_MAPPED = "partially_mapped", "Partially mapped"
    MAPPED = "mapped", "Mapped"
    VERIFIED = "verified", "Verified"


class ZoneStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"
    NEEDS_REPAIR = "needs_repair", "Needs repair"
    SEASONAL = "seasonal", "Seasonal"
    UNKNOWN = "unknown", "Unknown"


class ComponentType(models.TextChoices):
    HEAD = "head", "Sprinkler head"
    EMITTER = "emitter", "Drip emitter"
    VALVE = "valve", "Valve"
    CONTROLLER = "controller", "Controller"
    SHUTOFF = "shutoff", "Shutoff"
    BACKFLOW = "backflow", "Backflow device"
    PIPE = "pipe", "Pipe / line"
    OTHER = "other", "Other"


class ComponentCondition(models.TextChoices):
    GOOD = "good", "Good"
    NEEDS_ADJUSTMENT = "needs_adjustment", "Needs adjustment"
    LEAKING = "leaking", "Leaking"
    CLOGGED = "clogged", "Clogged"
    BROKEN = "broken", "Broken"
    BURIED = "buried", "Buried / missing"
    UNKNOWN = "unknown", "Unknown"


class EventType(models.TextChoices):
    REPAIR = "repair", "Repair"
    OBSERVATION = "observation", "Observation"
    SCHEDULE_CHANGE = "schedule_change", "Schedule change"
    STARTUP = "startup", "Spring startup"
    WINTERIZATION = "winterization", "Winterization"
    OTHER = "other", "Other"


class IrrigationZone(models.Model):
    """One irrigation zone. `code` is the permanent ID history hangs off;
    `name` is renamable once the zone's purpose is understood (PDD 8.2)."""

    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    code = models.CharField(max_length=10, unique=True, editable=False)
    name = models.CharField(max_length=100)
    controller_station = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Station number on the controller, when known."
    )
    zone_type = models.CharField(
        max_length=10, choices=ZoneType.choices, default=ZoneType.UNKNOWN
    )
    investigation_status = models.CharField(
        max_length=20,
        choices=InvestigationStatus.choices,
        default=InvestigationStatus.UNKNOWN,
    )
    beds = models.ManyToManyField(Bed, blank=True, related_name="irrigation_zones")
    schedule_notes = models.TextField(
        blank=True, help_text="Typical runtime, seasonal changes, controller program."
    )
    last_verified_on = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=12, choices=ZoneStatus.choices, default=ZoneStatus.UNKNOWN
    )
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            with transaction.atomic():
                last = (
                    IrrigationZone.objects.select_for_update()
                    .order_by("-id")
                    .values_list("code", flat=True)
                    .first()
                )
                seq = int(last.split("-")[1]) + 1 if last else 1
                self.code = f"ZONE-{seq:02d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class IrrigationComponent(models.Model):
    """A head, valve, controller, or other physical piece of the system.

    `zone` is nullable on purpose: a component found in the yard before its
    zone is known is a valid record, not an error state.
    """

    zone = models.ForeignKey(
        IrrigationZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="components",
    )
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    component_type = models.CharField(max_length=10, choices=ComponentType.choices)
    bed = models.ForeignKey(
        Bed,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="irrigation_components",
    )
    location_note = models.CharField(
        max_length=200, blank=True, help_text='e.g. "NE corner, behind the rhododendron"'
    )
    condition = models.CharField(
        max_length=16, choices=ComponentCondition.choices, default=ComponentCondition.UNKNOWN
    )
    model_info = models.CharField(
        max_length=200, blank=True, help_text="Manufacturer / model / nozzle, when known."
    )
    photos = models.ManyToManyField(Photo, blank=True, related_name="irrigation_components")
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["component_type", "id"]

    def __str__(self):
        where = self.zone or self.bed or self.location_note or "unassigned"
        return f"{self.get_component_type_display()} ({where})"


class IrrigationEvent(models.Model):
    """Shared history: repairs, observations, schedule changes, winterization.

    Attached to a zone, a component, or both - at least one (DB-enforced).
    """

    zone = models.ForeignKey(
        IrrigationZone,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
    )
    component = models.ForeignKey(
        IrrigationComponent,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
    )
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    event_type = models.CharField(max_length=15, choices=EventType.choices)
    happened_on = models.DateField()
    notes = models.TextField(blank=True)
    photos = models.ManyToManyField(Photo, blank=True, related_name="irrigation_events")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-happened_on"]
        constraints = [
            models.CheckConstraint(
                name="irrigation_event_has_zone_or_component",
                condition=models.Q(zone__isnull=False) | models.Q(component__isnull=False),
            ),
        ]

    def __str__(self):
        target = self.zone or self.component
        return f"{self.get_event_type_display()} - {target} ({self.happened_on})"
