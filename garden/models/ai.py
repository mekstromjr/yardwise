"""AI suggestion records (PDD section 9): every AI response is stored as a
suggestion with an explicit user decision - accepted, dismissed, or saved for
later ("Not sure"). Nothing becomes a garden record without acceptance, and
the audit trail of what AI proposed survives either way."""

from django.conf import settings
from django.db import models

from .photos import Photo
from .plants import Plant


class SuggestionKind(models.TextChoices):
    IDENTIFY = "identify", "Identification"
    ENRICH = "enrich", "Record enrichment"
    QUESTION = "question", "Question"


class SuggestionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DISMISSED = "dismissed", "Dismissed"
    SAVED = "saved", "Saved for later"


class AISuggestion(models.Model):
    garden = models.ForeignKey(
        "garden.Garden", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    kind = models.CharField(max_length=8, choices=SuggestionKind.choices)
    question = models.TextField(blank=True)
    response = models.JSONField()
    photo = models.ForeignKey(Photo, null=True, blank=True, on_delete=models.SET_NULL)
    plant = models.ForeignKey(
        Plant, null=True, blank=True, on_delete=models.CASCADE, related_name="ai_suggestions"
    )
    status = models.CharField(
        max_length=9, choices=SuggestionStatus.choices, default=SuggestionStatus.PENDING
    )
    accepted_fields = models.JSONField(null=True, blank=True)  # enrichment audit
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} ({self.status})"
