"""Beds: the stable location registry.

No geometry in the MVP - the Property Map module later adds polygon/grid
columns to this table. `code` is the permanent identifier history hangs off;
`name` is the renamable display name (schema.md, R-014/R-018).
"""

from django.db import models, transaction

from .vocab import BedType


class Bed(models.Model):
    code = models.CharField(max_length=10, unique=True, editable=False)
    name = models.CharField(max_length=100)
    short_code = models.CharField(max_length=10, blank=True)
    bed_type = models.ForeignKey(BedType, null=True, blank=True, on_delete=models.PROTECT)
    sun_notes = models.TextField(blank=True)
    soil_notes = models.TextField(blank=True)
    irrigation_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            # Display names unique among active beds; archived beds free the name.
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(archived_at__isnull=True),
                name="unique_active_bed_name",
            ),
            models.UniqueConstraint(
                fields=["short_code"],
                condition=models.Q(archived_at__isnull=True) & ~models.Q(short_code=""),
                name="unique_active_bed_short_code",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            with transaction.atomic():
                last = (
                    Bed.objects.select_for_update()
                    .order_by("-id")
                    .values_list("code", flat=True)
                    .first()
                )
                seq = int(last.split("-")[1]) + 1 if last else 1
                self.code = f"BED-{seq:03d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
