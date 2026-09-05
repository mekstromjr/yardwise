"""Backfill per-user gardens (tenancy retrofit).

Every scoped row is assigned a garden:
- rows with a creator (created_by / uploaded_by / user) get that user's garden;
- creatorless rows (Bed, ProblemType, IrrigationZone/Component, Variety,
  ClimateProfile, and any row whose creator FK was nulled) go to the garden of
  the earliest-created user - the pre-tenancy install's owner;
- if no users exist at all, rows are left with garden=NULL.

Uses apps.get_model + a local for_user equivalent: historical models carry no
custom methods.
"""

from django.conf import settings
from django.db import migrations

# model name -> creator FK field ("" = no creator field on the model)
SCOPED_MODELS = {
    "Bed": "",
    "Plant": "created_by",
    "Photo": "uploaded_by",
    "Task": "created_by",
    "JournalEntry": "created_by",
    "HarvestEvent": "created_by",
    "Activity": "created_by",
    "ProblemType": "",
    "ProblemCase": "created_by",
    "IrrigationZone": "",
    "IrrigationComponent": "",
    "IrrigationEvent": "created_by",
    "Variety": "",
    "SeasonalPlanting": "created_by",
    "ClimateProfile": "",
    "AISuggestion": "created_by",
    "Notification": "user",
}


def backfill(apps, schema_editor):
    Garden = apps.get_model("garden", "Garden")
    User = apps.get_model(settings.AUTH_USER_MODEL)

    gardens = {}  # user id -> garden id

    def garden_for(user_id):
        if user_id not in gardens:
            garden, _created = Garden.objects.get_or_create(owner_id=user_id)
            gardens[user_id] = garden.pk
        return gardens[user_id]

    first_user = User.objects.order_by("id").first()
    default_garden_id = garden_for(first_user.pk) if first_user else None

    for model_name, creator_field in SCOPED_MODELS.items():
        Model = apps.get_model("garden", model_name)
        rows = Model.objects.filter(garden__isnull=True)
        if creator_field:
            creator_ids = (
                rows.filter(**{f"{creator_field}__isnull": False})
                .values_list(f"{creator_field}_id", flat=True)
                .distinct()
            )
            for user_id in creator_ids:
                rows.filter(**{f"{creator_field}_id": user_id}).update(
                    garden_id=garden_for(user_id)
                )
        if default_garden_id is not None:
            rows.filter(garden__isnull=True).update(garden_id=default_garden_id)


def noop(apps, schema_editor):
    """Reverse: keep the data (archive-not-delete); the FKs are nullable."""


class Migration(migrations.Migration):
    dependencies = [
        ("garden", "0009_garden_remove_bed_unique_active_bed_name_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
