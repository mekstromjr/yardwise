"""Property map views (PDD section 4 MVP): view, trace, place, identify."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Bed, MapLayer, Plant, PlantLocation, PropertyMap
from .tenancy import garden_for


@login_required
def map_page(request):
    g = garden_for(request)
    pmap = PropertyMap.get(g)
    focus_plant = request.GET.get("plant", "")
    focus_bed = request.GET.get("bed", "")
    return render(request, "garden/map/map.html", {
        "nav": "map",
        "pmap": pmap,
        "layers": MapLayer.objects.filter(garden=g, archived_at__isnull=True),
        "focus_plant": focus_plant,
        "focus_bed": focus_bed,
        "beds": Bed.objects.filter(garden=g, archived_at__isnull=True),
        "plants": Plant.objects.filter(garden=g, status="active"),
    })


@login_required
def map_data(request):
    """Everything the map JS renders, in one payload."""
    g = garden_for(request)
    pmap = PropertyMap.get(g)
    beds = []
    for bed in Bed.objects.filter(garden=g, archived_at__isnull=True):
        beds.append({
            "id": bed.pk, "code": bed.code, "name": bed.name,
            "boundary": bed.boundary,
            "cells": pmap.cells_for_polygon(bed.boundary or []),
        })
    points = []
    for loc in (
        PlantLocation.objects.filter(is_current=True, point_x__isnull=False,
                                     plant__garden=g, plant__status="active")
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
         "visible": la.visible, "opacity": la.opacity,
         "w": la.natural_width, "h": la.natural_height}
        for la in MapLayer.objects.filter(garden=g, archived_at__isnull=True)
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
    g = garden_for(request)
    bed = get_object_or_404(Bed, pk=pk, garden=g, archived_at__isnull=True)
    payload = json.loads(request.body)
    boundary = payload.get("boundary")
    if boundary is not None and (
        not isinstance(boundary, list) or len(boundary) < 3
        or not all(isinstance(p, list) and len(p) == 2 for p in boundary)
    ):
        return JsonResponse({"error": "boundary must be [[x,y],...] with 3+ points"}, status=400)
    bed.boundary = boundary
    bed.save(update_fields=["boundary"])
    cells = PropertyMap.get(g).cells_for_polygon(boundary or [])
    return JsonResponse({"ok": True, "cells": cells})


@require_POST
@login_required
def plant_point(request, pk):
    """Place/move a plant's current location point: {"x": .., "y": ..}.

    Creates a current PlantLocation if the plant has none; when the point
    lands inside a traced bed, the location's bed is set from geometry
    (R-023: map selection resolves the containing bed automatically).
    """
    g = garden_for(request)
    plant = get_object_or_404(Plant, pk=pk, garden=g)
    payload = json.loads(request.body)
    x, y = float(payload["x"]), float(payload["y"])
    loc = plant.current_locations.first()
    if loc is None:
        loc = PlantLocation.objects.create(plant=plant)
    loc.point_x, loc.point_y = x, y
    containing = _bed_containing(g, x, y)
    if containing and loc.bed_id != containing.pk:
        loc.bed = containing
    loc.save()
    pmap = PropertyMap.get(g)
    return JsonResponse({"ok": True, "cell": pmap.cell_for(x, y),
                         "bed": loc.bed.name if loc.bed else ""})


def _bed_containing(garden, x: float, y: float):
    """Point-in-polygon (ray casting) over traced beds."""
    for bed in Bed.objects.filter(garden=garden, archived_at__isnull=True,
                                  boundary__isnull=False):
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


def _promote_layer(garden, layer) -> bool:
    """Most-recent-wins: the layer the user just added becomes the primary
    view; older layers stay as hidden reference toggles (PDD: keep prior
    imagery; replacing it never moves structured data, R-043). Returns
    whether this is the property's first layer (which sizes the map)."""
    others = MapLayer.objects.filter(
        garden=garden, archived_at__isnull=True
    ).exclude(pk=layer.pk)
    was_first = not others.exists()
    others.update(is_primary=False, visible=False)
    if not (layer.is_primary and layer.visible):
        layer.is_primary = True
        layer.visible = True
        layer.save(update_fields=["is_primary", "visible"])
    return was_first


@require_POST
@login_required
def layer_upload(request):
    """Upload an aerial/reference image. The newest layer becomes the view;
    the first one ever also sizes the coordinate space from its pixels."""
    from PIL import Image as PILImage

    g = garden_for(request)
    image = request.FILES["image"]
    name = request.POST.get("name") or image.name
    layer = MapLayer.objects.create(name=name, image=image, garden=g)
    layer.image.open("rb")
    with PILImage.open(layer.image) as im:
        layer.natural_width, layer.natural_height = float(im.width), float(im.height)
    layer.save(update_fields=["natural_width", "natural_height"])
    _promote_layer(g, layer)
    _maybe_resize_space(g, layer)
    return redirect("map")


def _map_has_geometry(garden) -> bool:
    return (
        Bed.objects.filter(garden=garden, archived_at__isnull=True,
                           boundary__isnull=False).exists()
        or PlantLocation.objects.filter(is_current=True, point_x__isnull=False,
                                        plant__garden=garden).exists()
    )


def _maybe_resize_space(garden, layer) -> None:
    """Size the coordinate space to the new primary image whenever nothing is
    traced or placed yet - with no geometry there is nothing to move (R-043).
    Once beds/points exist the space is frozen and images letterbox instead."""
    if layer.natural_width and layer.natural_height and not _map_has_geometry(garden):
        pmap = PropertyMap.get(garden)
        pmap.width, pmap.height = layer.natural_width, layer.natural_height
        pmap.save(update_fields=["width", "height"])


ESRI_EXPORT = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
    "MapServer/export"
)
NOMINATIM = "https://nominatim.openstreetmap.org/search"
CENSUS = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
)


def _geocode(address: str):
    """US Census first (built for exactly the 'street, city, state zip' form
    people type; Nominatim's free-form parser often whiffs on it), then
    Nominatim as the fallback for anything Census can't place.
    Returns (lat, lon) or None."""
    import urllib.parse
    import urllib.request

    def fetch(url):
        req = urllib.request.Request(url, headers={"User-Agent": "yardwise-selfhosted/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())

    try:
        q = urllib.parse.urlencode({
            "address": address, "benchmark": "Public_AR_Current", "format": "json",
        })
        matches = fetch(f"{CENSUS}?{q}")["result"]["addressMatches"]
        if matches:
            c = matches[0]["coordinates"]
            return float(c["y"]), float(c["x"])
    except Exception:  # noqa: BLE001 - any census hiccup just falls through
        pass
    try:
        q = urllib.parse.urlencode({"q": address, "format": "json", "limit": 1})
        hits = fetch(f"{NOMINATIM}?{q}")
        if hits:
            return float(hits[0]["lat"]), float(hits[0]["lon"])
    except Exception:  # noqa: BLE001
        pass
    return None


@require_POST
@login_required
def satellite_fetch(request):
    """Fetch satellite imagery for an address as a reference layer.

    Geocodes via OpenStreetMap Nominatim, then pulls an Esri World Imagery
    export (free with attribution - shown on the map page). Like any layer,
    it's reference-only: swapping it never moves structured data (R-043).
    """
    import urllib.error
    import urllib.parse
    import urllib.request

    from django.core.files.base import ContentFile

    g = garden_for(request)
    address = request.POST.get("address", "").strip()
    span_m = min(max(int(request.POST.get("span_m") or 150), 40), 1000)
    if not address:
        return redirect("map")
    coords = _geocode(address)
    if coords is None:
        return _map_error(
            request,
            f'Couldn\'t find "{address}" on the map - check the spelling, '
            "or try just street + city + state (no unit numbers).",
        )
    lat, lon = coords
    try:
        # meters -> degrees (lon corrected by latitude)
        import math

        dlat = span_m / 111_320
        dlon = span_m / (111_320 * max(math.cos(math.radians(lat)), 0.1))
        bbox = f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"
        q2 = urllib.parse.urlencode({
            "bbox": bbox, "bboxSR": "4326", "size": "1280,1280",
            "format": "png", "f": "image",
        })
        image_bytes = None
        for attempt in (1, 2):  # the export can be slow; one retry beats a 500
            try:
                with urllib.request.urlopen(f"{ESRI_EXPORT}?{q2}", timeout=25) as r:
                    image_bytes = r.read()
                break
            except urllib.error.URLError:
                if attempt == 2:
                    raise
    except (urllib.error.URLError, ValueError, KeyError):
        msg = ("Found the address, but the satellite imagery service "
               "didn't answer - try again in a minute.")
        return _map_error(request, msg)
    layer = MapLayer(name=f"Satellite - {address[:60]}", garden=g,
                     natural_width=1280.0, natural_height=1280.0)
    layer.image.save("satellite.png", ContentFile(image_bytes), save=True)
    _promote_layer(g, layer)
    _maybe_resize_space(g, layer)
    return redirect("map")


def _map_error(request, msg):
    g = garden_for(request)
    pmap = PropertyMap.get(g)
    return render(request, "garden/map/map.html", {
        "nav": "map", "pmap": pmap, "error": msg,
        "layers": MapLayer.objects.filter(garden=g, archived_at__isnull=True),
        "focus_plant": "", "focus_bed": "",
        "beds": Bed.objects.filter(garden=g, archived_at__isnull=True),
        "plants": Plant.objects.filter(garden=g, status="active"),
    })
