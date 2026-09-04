"""Vegetable Garden Planner screens (#24).

Kept out of views.py on purpose: the planner is a self-contained module and
its forms live here with it. Everything is server-rendered; the one-click
actions are plain POST forms (no-JS friendly, htmx optional later).
"""

import datetime

from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Bed,
    ClimateProfile,
    GrowAgain,
    GrowingMethod,
    PlantingStatus,
    SeasonalPlanting,
    Variety,
)


class VarietyForm(forms.ModelForm):
    class Meta:
        model = Variety
        fields = [
            "name", "cultivar", "botanical_name", "crop_family",
            "days_to_maturity", "spacing_notes",
            "start_indoors_weeks_before_lf", "transplant_weeks_after_lf",
            "direct_sow_weeks", "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class PlantingForm(forms.ModelForm):
    class Meta:
        model = SeasonalPlanting
        fields = [
            "variety", "year", "bed", "growing_method", "status",
            "planned_quantity", "sowed_on", "transplanted_on",
            "first_harvest_on", "last_harvest_on", "season_notes",
        ]
        widgets = {
            "sowed_on": forms.DateInput(attrs={"type": "date"}),
            "transplanted_on": forms.DateInput(attrs={"type": "date"}),
            "first_harvest_on": forms.DateInput(attrs={"type": "date"}),
            "last_harvest_on": forms.DateInput(attrs={"type": "date"}),
            "season_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["variety"].queryset = Variety.objects.filter(archived_at__isnull=True)
        self.fields["bed"].queryset = Bed.objects.filter(archived_at__isnull=True)
        self.fields["bed"].empty_label = "(no bed yet)"


class ClimateForm(forms.ModelForm):
    class Meta:
        model = ClimateProfile
        fields = [
            "hardiness_zone",
            "avg_last_frost_month", "avg_last_frost_day",
            "avg_first_frost_month", "avg_first_frost_day",
            "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class CloseSeasonForm(forms.Form):
    grow_again = forms.ChoiceField(
        choices=[("", "Undecided"), *GrowAgain.choices], required=False, label="Grow again?"
    )
    closing_note = forms.CharField(
        required=False, label="Season notes", widget=forms.Textarea(attrs={"rows": 3})
    )


@login_required
def planner_home(request):
    current_year = datetime.date.today().year
    try:
        year = int(request.GET.get("year", current_year))
    except ValueError:
        year = current_year

    plantings = (
        SeasonalPlanting.objects.filter(year=year, archived_at__isnull=True)
        .select_related("variety", "bed")
    )
    climate = ClimateProfile.load()

    # Group by bed; unassigned plantings form their own group at the end.
    groups: dict[int | None, dict] = {}
    for p in plantings:
        p.milestone_list = p.compute_milestones(climate)
        p.conflicts = list(p.rotation_conflicts()) if p.status != PlantingStatus.FINISHED else []
        key = p.bed_id
        groups.setdefault(key, {"bed": p.bed, "plantings": []})["plantings"].append(p)
    bed_groups = sorted(
        groups.values(), key=lambda g: (g["bed"] is None, g["bed"].name if g["bed"] else "")
    )

    years = SeasonalPlanting.objects.values_list("year", flat=True).distinct()
    year_choices = sorted({current_year, current_year + 1, year, *years})

    return render(request, "garden/planner/home.html", {
        "nav": "plants",
        "year": year,
        "year_choices": year_choices,
        "bed_groups": bed_groups,
        "climate": climate,
        "climate_ready": climate.last_frost_date(year) is not None,
        "has_varieties": Variety.objects.filter(archived_at__isnull=True).exists(),
    })


@login_required
def planting_form(request, pk=None):
    planting = get_object_or_404(SeasonalPlanting, pk=pk) if pk else None
    initial = {} if planting else {"year": datetime.date.today().year}
    form = PlantingForm(request.POST or None, instance=planting, initial=initial)
    if request.method == "POST" and form.is_valid():
        planting = form.save(commit=False)
        if not planting.created_by_id:
            planting.created_by = request.user
        planting.save()
        return redirect(f"/planner/?year={planting.year}")
    return render(request, "garden/planner/planting_form.html", {
        "nav": "plants", "form": form, "planting": planting,
    })


@login_required
def mark_planted(request, pk):
    """One-click 'Mark as Planted' (PDD 6.2): sets status and the
    method-appropriate actual date. Idempotent-ish: never overwrites a date
    the user already recorded."""
    planting = get_object_or_404(SeasonalPlanting, pk=pk, archived_at__isnull=True)
    if request.method == "POST":
        today = datetime.date.today()
        planting.status = PlantingStatus.PLANTED
        if planting.growing_method == GrowingMethod.DIRECT_SOW:
            planting.sowed_on = planting.sowed_on or today
        else:
            planting.transplanted_on = planting.transplanted_on or today
        planting.save()
    return redirect(f"/planner/?year={planting.year}")


@login_required
def close_planting(request, pk):
    """End-of-season close (PDD 6.13): finished + grow-again rating + notes."""
    planting = get_object_or_404(SeasonalPlanting, pk=pk, archived_at__isnull=True)
    form = CloseSeasonForm(request.POST or None, initial={
        "grow_again": planting.grow_again, "closing_note": planting.season_notes,
    })
    if request.method == "POST" and form.is_valid():
        planting.status = PlantingStatus.FINISHED
        planting.grow_again = form.cleaned_data["grow_again"]
        planting.season_notes = form.cleaned_data["closing_note"]
        planting.save()
        return redirect(f"/planner/?year={planting.year}")
    return render(request, "garden/planner/close_form.html", {
        "nav": "plants", "form": form, "planting": planting,
    })


@login_required
def variety_list(request):
    varieties = Variety.objects.filter(archived_at__isnull=True)
    return render(request, "garden/planner/variety_list.html", {
        "nav": "plants", "varieties": varieties,
    })


@login_required
def variety_form(request, pk=None):
    variety = get_object_or_404(Variety, pk=pk) if pk else None
    form = VarietyForm(request.POST or None, instance=variety)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("variety-list")
    return render(request, "garden/planner/variety_form.html", {
        "nav": "plants", "form": form, "variety": variety,
    })


@login_required
def climate_form(request):
    profile = ClimateProfile.load()
    form = ClimateForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("planner")
    return render(request, "garden/planner/climate_form.html", {
        "nav": "plants", "form": form, "profile": profile,
    })
