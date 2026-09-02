"""Seed the user-editable vocabulary (garden/seeds.py).

Seeded rows get is_builtin=True: protected from deletion in the UI, but
renamable and archivable - they are defaults, not rules.
"""

from django.db import migrations

from garden import seeds


def seed(apps, schema_editor):
    simple = {
        "PlantType": seeds.PLANT_TYPES,
        "BedType": seeds.BED_TYPES,
        "ActivityType": seeds.ACTIVITY_TYPES,
        "TaskCategory": seeds.TASK_CATEGORIES,
        "HarvestUnit": seeds.HARVEST_UNITS,
        "PhotoCategory": seeds.PHOTO_CATEGORIES,
    }
    for model_name, names in simple.items():
        model = apps.get_model("garden", model_name)
        for name in names:
            model.objects.get_or_create(name=name, defaults={"is_builtin": True})

    window = apps.get_model("garden", "SeasonWindow")
    for label, sm, sd, em, ed in seeds.SEASON_WINDOWS:
        window.objects.get_or_create(
            label=label,
            defaults={
                "start_month": sm,
                "start_day": sd,
                "end_month": em,
                "end_day": ed,
                "is_builtin": True,
            },
        )


def unseed(apps, schema_editor):
    # Reverse: remove only untouched builtin rows; user data is never deleted.
    for model_name in (
        "PlantType", "BedType", "ActivityType", "TaskCategory", "HarvestUnit", "PhotoCategory"
    ):
        apps.get_model("garden", model_name).objects.filter(is_builtin=True).delete()
    apps.get_model("garden", "SeasonWindow").objects.filter(is_builtin=True).delete()


class Migration(migrations.Migration):
    dependencies = [("garden", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
