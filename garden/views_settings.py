"""Settings & vocabulary management (PDD screen 8) and the bed registry (#10).

One settings page manages every vocabulary table with the same three verbs:
rename, add, archive. Builtin rows are renamable but never deletable; nothing
here hard-deletes (archive-not-delete rule).
"""

import datetime

import django.utils.timezone as tz
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from . import models
from .forms import BedForm
from .tenancy import garden_for

VOCABULARIES = {
    # slug -> (model, singular label, plural heading)
    "plant-types": (models.PlantType, "plant type", "Plant types"),
    "bed-types": (models.BedType, "bed type", "Bed types"),
    "activity-types": (models.ActivityType, "activity type", "Activity types"),
    "task-categories": (models.TaskCategory, "task category", "Task categories"),
    "harvest-units": (models.HarvestUnit, "harvest unit", "Harvest units"),
    "photo-categories": (models.PhotoCategory, "photo category", "Photo categories"),
    "tags": (models.Tag, "tag", "Tags"),
}


@login_required
def settings_home(request):
    sections = [
        {
            "slug": slug,
            "label": label,
            "plural": plural,
            "items": model.objects.filter(archived_at__isnull=True),
        }
        for slug, (model, label, plural) in VOCABULARIES.items()
    ]
    return render(request, "garden/settings/home.html", {
        "nav": "me",
        "sections": sections,
        "windows": models.SeasonWindow.objects.filter(archived_at__isnull=True),
        "months": [(m, datetime.date(2000, m, 1).strftime("%B")) for m in range(1, 13)],
    })


@login_required
def vocab_action(request, slug):
    """POST add/rename/archive for one vocabulary table."""
    model, _label, _plural = VOCABULARIES[slug]
    if request.method != "POST":
        return redirect("settings")
    action = request.POST.get("action")
    if action == "add":
        name = request.POST.get("name", "").strip()
        if name:
            model.objects.get_or_create(name=name)
    else:
        item = get_object_or_404(model, pk=request.POST.get("pk"))
        if action == "rename":
            name = request.POST.get("name", "").strip()
            if name:
                item.name = name
                item.save(update_fields=["name"])
        elif action == "archive" and not item.is_builtin:
            item.archived_at = tz.now()
            item.save(update_fields=["archived_at"])
    return redirect("settings")


@login_required
def window_action(request):
    """POST edit/add for season windows."""
    if request.method != "POST":
        return redirect("settings")
    pk = request.POST.get("pk")
    window = get_object_or_404(models.SeasonWindow, pk=pk) if pk else models.SeasonWindow()
    label = request.POST.get("label", "").strip()
    if label:
        window.label = label
    try:
        window.start_month = int(request.POST["start_month"])
        window.start_day = int(request.POST["start_day"])
        window.end_month = int(request.POST["end_month"])
        window.end_day = int(request.POST["end_day"])
    except (KeyError, ValueError):
        return redirect("settings")
    if window.label:
        window.save()
    return redirect("settings")


# --- Bed registry -----------------------------------------------------------


@login_required
def bed_list(request):
    beds = models.Bed.objects.filter(
        garden=garden_for(request), archived_at__isnull=True
    ).select_related("bed_type")
    for bed in beds:
        bed.plant_count = bed.plant_locations.filter(
            is_current=True, plant__status="active"
        ).count()
    return render(request, "garden/beds/list.html", {"nav": "me", "beds": beds})


@login_required
def bed_form(request, pk=None):
    g = garden_for(request)
    bed = get_object_or_404(models.Bed, pk=pk, garden=g) if pk else None
    form = BedForm(request.POST or None, instance=bed, garden=g)
    if request.method == "POST" and form.is_valid():
        bed = form.save(commit=False)
        bed.garden = g
        bed.save()
        return redirect("bed-detail", pk=bed.pk)
    plants = (
        bed.plant_locations.filter(is_current=True, plant__status="active").select_related("plant")
        if bed else []
    )
    return render(request, "garden/beds/form.html", {
        "nav": "me", "form": form, "bed": bed, "plants": plants,
    })


@login_required
def bed_archive(request, pk):
    bed = get_object_or_404(models.Bed, pk=pk, garden=garden_for(request))
    if request.method == "POST":
        current = bed.plant_locations.filter(is_current=True, plant__status="active").count()
        if current == 0:  # refuse to archive a bed that still holds plants
            bed.archived_at = tz.now()
            bed.save(update_fields=["archived_at"])
    return redirect("bed-list")
