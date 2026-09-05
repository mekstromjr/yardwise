"""Per-user gardens (#tenancy).

Every account gets its own private garden; scoped models carry a nullable
``garden`` FK and views filter by the request user's garden. Sharing between
users is a future ticket (#27) - hence a Garden row with an ``owner`` FK
(rather than raw user FKs on every model) so a membership table can slot in
later without another schema sweep. Until then one user owns exactly one
garden, enforced by a unique constraint on ``owner``.
"""

from django.conf import settings
from django.db import models


class Garden(models.Model):
    name = models.CharField(max_length=100, default="My garden")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gardens"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # One garden per owner for now; future sharing (#27) relaxes this
            # via a membership table, not by loosening the owner FK.
            models.UniqueConstraint(fields=["owner"], name="unique_garden_owner"),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner})"

    @classmethod
    def for_user(cls, user) -> "Garden":
        garden, _created = cls.objects.get_or_create(owner=user)
        return garden
