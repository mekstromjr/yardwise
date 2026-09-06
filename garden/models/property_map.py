"""Property map (PDD section 4, MVP slice).

Coordinate model: the map lives in a flat "map units" space (Leaflet
CRS.Simple - no geo-referencing). The primary aerial image defines the space:
its pixel dimensions become the map's width/height. The structured data
(bed polygons, plant points) is authoritative; aerial images are reference
layers that can be hidden or replaced without moving anything (R-043).

The stable alphanumeric grid (A1, B4...) is an overlay derived from the map
dimensions and the configured column/row counts; cells are computed from
geometry, never stored (R-013, and consistent with materialize-vs-derive:
geometry is the stored truth, grid references derive from it).
"""

from django.core.exceptions import ValidationError
from django.db import models


class MapLayerKind(models.TextChoices):
    MASTER = "master", "Master property map"
    AERIAL = "aerial", "Aerial / historical imagery"
    REFERENCE = "reference", "Other reference imagery"


class PropertyMap(models.Model):
    """One per garden: the coordinate space + grid configuration."""

    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    width = models.FloatField(default=1000)
    height = models.FloatField(default=750)
    grid_cols = models.PositiveSmallIntegerField(default=10)
    grid_rows = models.PositiveSmallIntegerField(default=8)
    grid_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "property map"

    def __str__(self):
        return f"Property map ({self.width:g}x{self.height:g})"

    @classmethod
    def get(cls, garden=None) -> "PropertyMap":
        obj, _ = cls.objects.get_or_create(garden=garden)
        return obj

    def cell_for(self, x: float, y: float) -> str:
        """Grid reference (A1 top-left) for a map point; '' if out of bounds."""
        if not (0 <= x <= self.width and 0 <= y <= self.height):
            return ""
        col = min(int(x / self.width * self.grid_cols), self.grid_cols - 1)
        row = min(int(y / self.height * self.grid_rows), self.grid_rows - 1)
        return f"{_col_label(col)}{row + 1}"

    def cells_for_polygon(self, points: list) -> list[str]:
        """All grid cells a polygon's bounding box touches (approximation that
        errs toward inclusion - fine for search/filter purposes)."""
        if not points:
            return []
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        cells = []
        col_w = self.width / self.grid_cols
        row_h = self.height / self.grid_rows
        c0, c1 = int(min(xs) // col_w), int(max(xs) // col_w)
        r0, r1 = int(min(ys) // row_h), int(max(ys) // row_h)
        for r in range(max(r0, 0), min(r1, self.grid_rows - 1) + 1):
            for c in range(max(c0, 0), min(c1, self.grid_cols - 1) + 1):
                cells.append(f"{_col_label(c)}{r + 1}")
        return cells


def _col_label(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA (spreadsheet style)."""
    label = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        label = chr(65 + rem) + label
    return label


def aerial_upload_path(instance, filename: str) -> str:
    return f"map/{filename}"


class MapLayer(models.Model):
    """A reference image (aerial photo, hand-drawn plan). Hiding or replacing
    one never moves structured data."""

    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to=aerial_upload_path)
    kind = models.CharField(
        max_length=12, choices=MapLayerKind.choices, default=MapLayerKind.REFERENCE
    )
    version = models.PositiveSmallIntegerField(null=True, blank=True)
    source_sha256 = models.CharField(max_length=64, blank=True, editable=False)
    immutable_original = models.BooleanField(default=False)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="revisions"
    )
    is_primary = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)
    opacity = models.FloatField(default=1.0)
    # Natural pixel size, recorded at save. The renderer fits the image into
    # the coordinate space PRESERVING this ratio (letterboxed) instead of
    # stretching it to the space's bounds.
    natural_width = models.FloatField(null=True, blank=True)
    natural_height = models.FloatField(null=True, blank=True)
    # Placement within the permanent property coordinate canvas. A future
    # master revision is aligned here; established geometry never moves.
    canvas_x = models.FloatField(null=True, blank=True)
    canvas_y = models.FloatField(null=True, blank=True)
    canvas_width = models.FloatField(null=True, blank=True)
    canvas_height = models.FloatField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_primary", "-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["garden", "version"],
                condition=models.Q(kind=MapLayerKind.MASTER),
                name="unique_master_map_version_per_garden",
            ),
            models.UniqueConstraint(
                fields=["garden"],
                condition=(
                    models.Q(kind=MapLayerKind.MASTER, is_primary=True)
                    & models.Q(archived_at__isnull=True)
                ),
                name="one_active_master_map_per_garden",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """A locked master keeps its exact source bytes and identity forever.

        Visibility and canvas alignment may change, but replacing the file or
        rewriting its recorded fingerprint always creates a new version.
        """
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and original.immutable_original:
                protected = (
                    "image", "kind", "version", "source_sha256",
                    "natural_width", "natural_height", "supersedes_id",
                )
                changed = [
                    field for field in protected
                    if str(getattr(self, field)) != str(getattr(original, field))
                ]
                if changed:
                    raise ValidationError(
                        "A locked master map cannot be overwritten; adopt a new version instead."
                    )
        super().save(*args, **kwargs)
