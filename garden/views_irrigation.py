"""Sprinkler & Irrigation screens (PDD 8, module #25).

Forms live here rather than in garden/forms.py to keep the module additive -
shared files only gain the import block and the URL group.
"""

import datetime

import django.utils.timezone as tz
from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MultiFileField
from .models import (
    Bed,
    InvestigationStatus,
    IrrigationComponent,
    IrrigationEvent,
    IrrigationZone,
)
from .tenancy import garden_for
from .views import _save_photos

# --- Forms ------------------------------------------------------------------


class IrrigationZoneForm(forms.ModelForm):
    class Meta:
        model = IrrigationZone
        fields = [
            "name", "controller_station", "zone_type", "investigation_status",
            "status", "beds", "schedule_notes", "last_verified_on", "notes",
        ]
        widgets = {
            "last_verified_on": forms.DateInput(attrs={"type": "date"}),
            "schedule_notes": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "beds": forms.SelectMultiple(attrs={"size": 4}),
        }
        labels = {
            "beds": "Beds this zone waters",
            "last_verified_on": "Last physically verified",
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        beds = Bed.objects.filter(archived_at__isnull=True)
        if garden is not None:
            beds = beds.filter(garden=garden)
        self.fields["beds"].queryset = beds
        self.fields["beds"].required = False


class IrrigationComponentForm(forms.ModelForm):
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        model = IrrigationComponent
        fields = [
            "component_type", "zone", "bed", "location_note",
            "condition", "model_info", "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"zone": "Zone (leave blank if unknown)"}

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        zones = IrrigationZone.objects.filter(archived_at__isnull=True)
        beds = Bed.objects.filter(archived_at__isnull=True)
        if garden is not None:
            zones = zones.filter(garden=garden)
            beds = beds.filter(garden=garden)
        self.fields["zone"].queryset = zones
        self.fields["bed"].queryset = beds


class IrrigationEventForm(forms.ModelForm):
    photos_upload = MultiFileField(required=False, label="Photos")

    class Meta:
        model = IrrigationEvent
        fields = ["event_type", "zone", "component", "happened_on", "notes"]
        widgets = {
            "happened_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, garden=None, **kwargs):
        super().__init__(*args, **kwargs)
        zones = IrrigationZone.objects.filter(archived_at__isnull=True)
        components = IrrigationComponent.objects.filter(archived_at__isnull=True)
        if garden is not None:
            zones = zones.filter(garden=garden)
            components = components.filter(garden=garden)
        self.fields["zone"].queryset = zones
        self.fields["component"].queryset = components

    def clean(self):
        data = super().clean()
        if not data.get("zone") and not data.get("component"):
            # Friendly mirror of the DB check constraint.
            raise forms.ValidationError("Attach this event to a zone, a component, or both.")
        return data


# --- Views ------------------------------------------------------------------

# Unknown first: the overview leads with what still needs figuring out.
_STATUS_ORDER = [
    InvestigationStatus.UNKNOWN,
    InvestigationStatus.PARTIALLY_MAPPED,
    InvestigationStatus.MAPPED,
    InvestigationStatus.VERIFIED,
]


@login_required
def irrigation_overview(request):
    g = garden_for(request)
    zones = IrrigationZone.objects.filter(
        garden=g, archived_at__isnull=True
    ).prefetch_related("beds")
    by_status = {status: [] for status in _STATUS_ORDER}
    for zone in zones:
        by_status[zone.investigation_status].append(zone)
    groups = [
        {
            "status": status,
            "label": InvestigationStatus(status).label,
            "zones": by_status[status],
        }
        for status in _STATUS_ORDER
        if by_status[status]
    ]
    unassigned = IrrigationComponent.objects.filter(
        garden=g, archived_at__isnull=True, zone__isnull=True
    ).select_related("bed")
    return render(request, "garden/irrigation/overview.html", {
        "nav": "irrigation",
        "groups": groups,
        "zone_count": len(zones),
        "unassigned": unassigned,
    })


@login_required
def zone_detail(request, pk):
    zone = get_object_or_404(IrrigationZone, pk=pk, garden=garden_for(request))
    events = (
        IrrigationEvent.objects.filter(Q(zone=zone) | Q(component__zone=zone))
        .select_related("component")
        .distinct()[:50]
    )
    return render(request, "garden/irrigation/zone_detail.html", {
        "nav": "irrigation",
        "zone": zone,
        "beds": zone.beds.filter(archived_at__isnull=True),
        "components": zone.components.filter(archived_at__isnull=True),
        "events": events,
    })


@login_required
def zone_form(request, pk=None):
    g = garden_for(request)
    zone = get_object_or_404(IrrigationZone, pk=pk, garden=g) if pk else None
    form = IrrigationZoneForm(request.POST or None, instance=zone, garden=g)
    if request.method == "POST" and form.is_valid():
        zone = form.save(commit=False)
        zone.garden = g
        zone.save()
        form.save_m2m()
        return redirect("irrigation-zone-detail", pk=zone.pk)
    return render(request, "garden/irrigation/zone_form.html",
                  {"nav": "irrigation", "zone": zone, "form": form})


@login_required
def zone_archive(request, pk):
    zone = get_object_or_404(IrrigationZone, pk=pk, garden=garden_for(request))
    if request.method == "POST":
        zone.archived_at = tz.now()
        zone.save(update_fields=["archived_at"])
    return redirect("irrigation-overview")


@login_required
def component_form(request, pk=None):
    g = garden_for(request)
    component = get_object_or_404(IrrigationComponent, pk=pk, garden=g) if pk else None
    form = IrrigationComponentForm(request.POST or None, request.FILES or None,
                                   instance=component, garden=g)
    if request.method == "POST" and form.is_valid():
        component = form.save(commit=False)
        component.garden = g
        component.save()
        form.save_m2m()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, garden=g):
            component.photos.add(photo)
        if component.zone_id:
            return redirect("irrigation-zone-detail", pk=component.zone_id)
        return redirect("irrigation-overview")
    if not pk:  # "Add component" from a zone page pre-selects that zone
        zone_id = request.GET.get("zone", "")
        if zone_id.isdigit():
            form.fields["zone"].initial = zone_id
    return render(request, "garden/irrigation/component_form.html",
                  {"nav": "irrigation", "component": component, "form": form})


@login_required
def event_add(request):
    initial = {"happened_on": datetime.date.today()}
    zone_id = request.GET.get("zone", "")
    if zone_id.isdigit():
        initial["zone"] = zone_id
    component_id = request.GET.get("component", "")
    if component_id.isdigit():
        initial["component"] = component_id
    g = garden_for(request)
    form = IrrigationEventForm(request.POST or None, request.FILES or None, initial=initial,
                               garden=g)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.garden = g
        event.save()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, garden=g):
            event.photos.add(photo)
        if event.zone_id:
            return redirect("irrigation-zone-detail", pk=event.zone_id)
        return redirect("irrigation-overview")
    return render(request, "garden/irrigation/event_form.html",
                  {"nav": "irrigation", "form": form})
