"""Photos: one row per uploaded image, linked from many records (R-068).

Records link to Photo through explicit typed M2M fields on their own models
(Plant.photos, JournalEntry.photos, ...) - never by re-uploading.
"""

import datetime

from django.conf import settings
from django.db import models

from .vocab import PhotoCategory


class Season(models.TextChoices):
    WINTER = "winter", "Winter"
    SPRING = "spring", "Spring"
    SUMMER = "summer", "Summer"
    FALL = "fall", "Fall"


def photo_upload_path(instance, filename: str) -> str:
    today = datetime.date.today()
    return f"photos/{today.year}/{today.month:02d}/{filename}"


class Photo(models.Model):
    file = models.ImageField(upload_to=photo_upload_path)
    # Derivatives generated on upload (issue #11) so a growing library stays
    # fast; templates fall back to `file` when absent.
    file_web = models.ImageField(upload_to=photo_upload_path, null=True, blank=True)
    file_thumb = models.ImageField(upload_to=photo_upload_path, null=True, blank=True)
    taken_on = models.DateField(null=True, blank=True)  # EXIF-derived, user-editable
    season = models.CharField(max_length=6, choices=Season.choices, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    caption = models.CharField(max_length=300, blank=True)
    categories = models.ManyToManyField(PhotoCategory, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_on", "-uploaded_at"]

    def __str__(self):
        return self.caption or f"Photo {self.pk}"

    @property
    def web_url(self) -> str:
        return (self.file_web or self.file).url

    @property
    def thumb_url(self) -> str:
        return (self.file_thumb or self.file).url

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new and self.file and not self.taken_on:
            self.taken_on = _exif_date(self.file)
        # Derive season/year from taken_on when not explicitly set (both stay
        # user-overridable - AI/heuristics suggest, the user decides).
        if self.taken_on:
            if not self.year:
                self.year = self.taken_on.year
            if not self.season:
                self.season = {
                    12: Season.WINTER, 1: Season.WINTER, 2: Season.WINTER,
                    3: Season.SPRING, 4: Season.SPRING, 5: Season.SPRING,
                    6: Season.SUMMER, 7: Season.SUMMER, 8: Season.SUMMER,
                    9: Season.FALL, 10: Season.FALL, 11: Season.FALL,
                }[self.taken_on.month]
        super().save(*args, **kwargs)
        if is_new and self.file and not self.file_web:
            self._make_derivatives()

    def _make_derivatives(self):
        """Web (1600px) and thumbnail (400px) JPEGs beside the original."""
        from io import BytesIO

        from django.core.files.base import ContentFile
        from PIL import Image, ImageOps

        try:
            with self.file.open("rb") as fh:
                original = Image.open(fh)
                original.load()
        except Exception:  # unreadable image: keep the original, skip derivatives
            return
        original = ImageOps.exif_transpose(original).convert("RGB")
        stem = self.file.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        for attr, size, quality in (("file_web", 1600, 82), ("file_thumb", 400, 75)):
            img = original.copy()
            img.thumbnail((size, size))
            buf = BytesIO()
            img.save(buf, "JPEG", quality=quality)
            getattr(self, attr).save(
                f"{stem}_{attr.split('_')[1]}.jpg", ContentFile(buf.getvalue()), save=False
            )
        super().save(update_fields=["file_web", "file_thumb"])


def _exif_date(file) -> datetime.date | None:
    from PIL import ExifTags, Image

    try:
        # seek, don't open/close: the upload hasn't been written to storage
        # yet, and closing it here would break the save that follows.
        file.seek(0)
        exif = Image.open(file).getexif()
        file.seek(0)
        raw = exif.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
        if not raw:
            ifd = exif.get_ifd(ExifTags.IFD.Exif)
            raw = ifd.get(ExifTags.Base.DateTimeOriginal)
        if raw:
            return datetime.datetime.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S").date()
    except Exception:
        pass
    return None
