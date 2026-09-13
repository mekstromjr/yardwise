from django.db import migrations


def trim_off_map_grid_cells(apps, schema_editor):
    PropertyMap = apps.get_model("garden", "PropertyMap")
    for property_map in PropertyMap.objects.all().iterator():
        if not property_map.grid_extent_width or not property_map.grid_extent_height:
            continue
        property_map.grid_cols = max(
            1,
            round(
                property_map.grid_cols
                * property_map.grid_extent_width
                / property_map.width
            ),
        )
        property_map.grid_rows = max(
            1,
            round(
                property_map.grid_rows
                * property_map.grid_extent_height
                / property_map.height
            ),
        )
        property_map.save(update_fields=["grid_cols", "grid_rows"])


def restore_canvas_grid_cells(apps, schema_editor):
    PropertyMap = apps.get_model("garden", "PropertyMap")
    for property_map in PropertyMap.objects.all().iterator():
        if not property_map.grid_extent_width or not property_map.grid_extent_height:
            continue
        property_map.grid_cols = max(
            1,
            round(
                property_map.grid_cols
                * property_map.width
                / property_map.grid_extent_width
            ),
        )
        property_map.grid_rows = max(
            1,
            round(
                property_map.grid_rows
                * property_map.height
                / property_map.grid_extent_height
            ),
        )
        property_map.save(update_fields=["grid_cols", "grid_rows"])


class Migration(migrations.Migration):
    dependencies = [
        ("garden", "0019_anchor_grid_to_master_map"),
    ]

    operations = [
        migrations.RunPython(trim_off_map_grid_cells, restore_canvas_grid_cells),
    ]
