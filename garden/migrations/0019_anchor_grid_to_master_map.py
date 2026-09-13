from django.db import migrations, models


def anchor_existing_grids(apps, schema_editor):
    MapLayer = apps.get_model("garden", "MapLayer")
    PropertyMap = apps.get_model("garden", "PropertyMap")
    for property_map in PropertyMap.objects.all().iterator():
        master = MapLayer.objects.filter(
            garden_id=property_map.garden_id,
            kind="master",
            is_primary=True,
            archived_at__isnull=True,
        ).first()
        if not master:
            property_map.grid_extent_width = property_map.width
            property_map.grid_extent_height = property_map.height
        elif master.canvas_width and master.canvas_height:
            property_map.grid_origin_x = master.canvas_x or 0
            property_map.grid_origin_y = master.canvas_y or 0
            property_map.grid_extent_width = master.canvas_width
            property_map.grid_extent_height = master.canvas_height
        elif master.natural_width and master.natural_height:
            scale = min(
                property_map.width / master.natural_width,
                property_map.height / master.natural_height,
            )
            property_map.grid_extent_width = master.natural_width * scale
            property_map.grid_extent_height = master.natural_height * scale
            property_map.grid_origin_x = (
                property_map.width - property_map.grid_extent_width
            ) / 2
            property_map.grid_origin_y = (
                property_map.height - property_map.grid_extent_height
            ) / 2
        else:
            property_map.grid_extent_width = property_map.width
            property_map.grid_extent_height = property_map.height
        property_map.save(update_fields=[
            "grid_origin_x", "grid_origin_y",
            "grid_extent_width", "grid_extent_height",
        ])


class Migration(migrations.Migration):
    dependencies = [
        ("garden", "0018_bed_primary_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertymap",
            name="grid_origin_x",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="propertymap",
            name="grid_origin_y",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="propertymap",
            name="grid_extent_width",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="propertymap",
            name="grid_extent_height",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.RunPython(anchor_existing_grids, migrations.RunPython.noop),
    ]
