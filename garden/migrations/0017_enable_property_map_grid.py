from django.db import migrations


def enable_property_map_grid(apps, schema_editor):
    PropertyMap = apps.get_model("garden", "PropertyMap")
    PropertyMap.objects.update(grid_visible=True)


def disable_property_map_grid(apps, schema_editor):
    PropertyMap = apps.get_model("garden", "PropertyMap")
    PropertyMap.objects.update(grid_visible=False)


class Migration(migrations.Migration):
    dependencies = [("garden", "0016_bed_photos")]

    operations = [
        migrations.RunPython(enable_property_map_grid, disable_property_map_grid),
    ]
