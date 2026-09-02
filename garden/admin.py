"""Admin registration - the owner's escape hatch, not the daily UI."""

from django.contrib import admin

from . import models


@admin.register(models.Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "short_code", "bed_type", "archived_at"]
    readonly_fields = ["code"]


@admin.register(models.Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ["common_name", "cultivar", "plant_type", "status"]
    search_fields = ["common_name", "botanical_name", "cultivar"]
    list_filter = ["status", "plant_type", "is_edible"]


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "schedule_kind", "priority", "archived_at"]


@admin.register(models.TaskOccurrence)
class TaskOccurrenceAdmin(admin.ModelAdmin):
    list_display = ["task", "due_on", "window_start", "window_end", "status"]
    list_filter = ["status"]


for model in (
    models.PlantLocation,
    models.Photo,
    models.Activity,
    models.JournalEntry,
    models.HarvestEvent,
    models.PlantType,
    models.BedType,
    models.ActivityType,
    models.TaskCategory,
    models.HarvestUnit,
    models.PhotoCategory,
    models.Tag,
    models.SeasonWindow,
):
    admin.site.register(model)
