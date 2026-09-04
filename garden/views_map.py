"""Property map views (PDD section 4 MVP): view, trace, place, identify."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Bed, MapLayer, Plant, PlantLocation, PropertyMap


@login_required
def map_page(request):
    pmap = PropertyMap.get()
    focus_plant = request.GET.get("plant", "")
    focus_bed = request.GET.get("bed", "")
    return render(request, "garden/map/map.html", {
        "nav": "plants",
        "pmap": pmap,
        "layers": MapLayer.objects.filter(archived_at__isnull=True),
        "focus_plant": focus_plant,
        "focus_bed": focus_bed,
        "beds": Bed.objects.filter(archived_at__isnull=True),
        "plants": Plant.objects.filter(status="active"),
    })


@login_required
def map_data(request):
    """Everything the map JS renders, in one payload."""
    pmap = PropertyMap.get()
    beds = []
    for bed in Bed.objects.filter(archived_at__isnull=True):
        beds.append({
            "id": bed.pk, "code": bed.code, "name": bed.name,
            "boundary": bed.boundary,
            "cells": pmap.cells_for_polygon(bed.boundary or []),
        })
    points = []
    for loc in (
        PlantLocation.objects.filter(is_current=True, point_x__isnull=False,
                                     plant__status="active")
        .select_related("plant", "bed")
    ):
        points.append({
            "loc_id": loc.pk, "plant_id": loc.plant_id,
            "name": str(loc.plant), "x": loc.point_x, "y": loc.point_y,
            "bed": loc.bed.name if loc.bed else "",
            "cell": pmap.cell_for(loc.point_x, loc.point_y),
            "url": f"/plants/{loc.plant_id}/",
        })
    layers = [
        {"id": la.pk, "name": la.name, "url": la.image.url, "primary": la.is_primary,
         "visible": la.visible, "opacity": la.opacity}
        for la in MapLayer.objects.filter(archived_at__isnull=True)
    ]
    return JsonResponse({
        "width": pmap.width, "height": pmap.height,
        "grid": {"cols": pmap.grid_cols, "rows": pmap.grid_rows,
                 "visible": pmap.grid_visible},
        "beds": beds, "points": points, "layers": layers,
    })


@require_POST
@login_required
def bed_boundary(request, pk):
    """Save a traced bed polygon: JSON body {"boundary": [[x,y], ...] | null}."""
    bed = get_object_or_404(Bed, pk=pk, archived_at__isnull=True)
    payload = json.loads(request.body)
    boundary = payload.get("boundary")
    if boundary is not None and (
        not isinstance(boundary, list) or len(boundary) < 3
        or not all(isinstance(p, list) and len(p) == 2 for p in boundary)
    ):
        return JsonResponse({"error": "boundary must be [[x,y],...] with 3+ points"}, status=400)
    bed.boundary = boundary
    bed.save(update_fields=["boundary"])
    return JsonResponse({"ok": True, "cells": PropertyMap.get().cells_for_polygon(boundary or [])})


@require_POST
@login_required
def plant_point(request, pk):
    """Place/move a plant's current location point: {"x": .., "y": ..}.

    Creates a current PlantLocation if the plant has none; when the point
    lands inside a traced bed, the location's bed is set from geometry
    (R-023: map selection resolves the containing bed automatically).
    """
    plant = get_object_or_404(Plant, pk=pk)
    payload = json.loads(request.body)
    x, y = float(payload["x"]), float(payload["y"])
    loc = plant.current_locations.first()
    if loc is None:
        loc = PlantLocation.objects.create(plant=plant)
    loc.point_x, loc.point_y = x, y
    containing = _bed_containing(x, y)
    if containing and loc.bed_id != containing.pk:
        loc.bed = containing
    loc.save()
    pmap = PropertyMap.get()
    return JsonResponse({"ok": True, "cell": pmap.cell_for(x, y),
                         "bed": loc.bed.name if loc.bed else ""})


def _bed_containing(x: float, y: float):
    """Point-in-polygon (ray casting) over traced beds."""
    for bed in Bed.objects.filter(archived_at__isnull=True, boundary__isnull=False):
        if _point_in_polygon(x, y, bed.boundary):
            return bed
    return None


def _point_in_polygon(x: float, y: float, poly: list) -> bool:
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


@require_POST
@login_required
def layer_upload(request):
    """Upload an aerial/reference image. The first one becomes primary and
    sizes the coordinate space from its pixels (R-037; replacing imagery
    later never moves structured data, R-043)."""
    from PIL import Image as PILImage

    image = request.FILES["image"]
    name = request.POST.get("name") or image.name
    is_first = not MapLayer.objects.filter(archived_at__isnull=True).exists()
    layer = MapLayer.objects.create(name=name, image=image, is_primary=is_first)
    if is_first:
        with PILImage.open(layer.image.path) as im:
            pmap = PropertyMap.get()
            pmap.width, pmap.height = float(im.width), float(im.height)
            pmap.save(update_fields=["width", "height"])
    return redirect("map")
