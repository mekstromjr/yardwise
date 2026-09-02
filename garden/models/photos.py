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

    def save(self, *args, **kwargs):
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
