import django.db.models.deletion
from django.db import migrations, models


def set_existing_bed_primary_photos(apps, schema_editor):
    Bed = apps.get_model("garden", "Bed")
    through = Bed.photos.through
    for bed in Bed.objects.filter(primary_photo__isnull=True).iterator():
        photo_id = (
            through.objects.filter(bed_id=bed.pk)
            .values_list("photo_id", flat=True)
            .first()
        )
        if photo_id:
            Bed.objects.filter(pk=bed.pk).update(primary_photo_id=photo_id)


class Migration(migrations.Migration):
    dependencies = [
        ("garden", "0017_enable_property_map_grid"),
    ]

    operations = [
        migrations.AddField(
            model_name="bed",
            name="primary_photo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="garden.photo",
            ),
        ),
        migrations.RunPython(set_existing_bed_primary_photos, migrations.RunPython.noop),
    ]
