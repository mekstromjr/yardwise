"""Property map views (PDD section 4 MVP): view, trace, place, identify."""

import hashlib
import io
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import ai
from .models import Bed, MapLayer, MapLayerKind, Plant, PlantLocation, PropertyMap
from .tenancy import garden_for

MASTER_MAP_FILENAME = "pnw-home-master-v1.png"
MASTER_MAP_SHA256 = "1185a0e9fbacecd937bfc9ed96de0401532669e89fe5be9dc223028a7c438cab"
MASTER_MAP_PATH = (
    Path(settings.BASE_DIR) / "garden" / "assets" / "master_maps" / MASTER_MAP_FILENAME
)


def _boundary_from_payload(payload):
    """Return a valid polygon boundary or None.

    Map writes share this validation so creating a bed from a new outline and
    adjusting an existing outline accept exactly the same shape.
    """
    boundary = payload.get("boundary")
    if (
        not isinstance(boundary, list)
        or len(boundary) < 3
        or not all(
            isinstance(point, list)
            and len(point) == 2
            and all(isinstance(value, int | float) for value in point)
            for point in boundary
        )
    ):
        return None
    return boundary


def _boundary_from_payload(payload):
    """Return a valid polygon boundary or None.

    Map writes share this validation so creating a bed from a new outline and
    adjusting an existing outline accept exactly the same shape.
    """
    boundary = payload.get("boundary")
    if (
        not isinstance(boundary, list)
        or len(boundary) < 3
        or not all(
            isinstance(point, list)
            and len(point) == 2
            and all(isinstance(value, int | float) for value in point)
            for point in boundary
        )
    ):
        return None
    return boundary


@login_required
def map_page(request):
    g = garden_for(request)
    pmap = PropertyMap.get(g)
    masters = MapLayer.objects.filter(
        garden=g, kind=MapLayerKind.MASTER, archived_at__isnull=True
    )
    active_master = masters.filter(is_primary=True).first()
    focus_plant = request.GET.get("plant", "")
    focus_bed = request.GET.get("bed", "")
    return render(request, "garden/map/map.html", {
        "nav": "map",
        "pmap": pmap,
        "layers": MapLayer.objects.filter(garden=g, archived_at__isnull=True),
        "active_master": active_master,
        "master_versions": masters.order_by("-version"),
        "bundled_master_installed": masters.filter(source_sha256=MASTER_MAP_SHA256).exists(),
        "reference_layers": MapLayer.objects.filter(
            garden=g, archived_at__isnull=True
        ).exclude(kind=MapLayerKind.MASTER),
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
            "url": reverse("bed-detail", args=[bed.pk]),
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
            "bed": loc.bed.name if loc.bed else "", "bed_id": loc.bed_id,
            "cell": pmap.cell_for(loc.point_x, loc.point_y),
            "url": reverse("plant-detail", args=[loc.plant_id]),
        })
    active_layers = MapLayer.objects.filter(garden=g, archived_at__isnull=True)
    # Base first, optional references above it.
    layer_rows = list(active_layers.filter(kind=MapLayerKind.MASTER).order_by("version"))
    layer_rows += list(active_layers.exclude(kind=MapLayerKind.MASTER).order_by("uploaded_at"))
    layers = [
        {"id": la.pk, "name": la.name, "url": la.image.url, "primary": la.is_primary,
         "visible": la.visible, "opacity": la.opacity,
         "kind": la.kind, "version": la.version,
         "w": la.natural_width, "h": la.natural_height,
         "x": la.canvas_x, "y": la.canvas_y,
         "render_w": la.canvas_width, "render_h": la.canvas_height}
        for la in layer_rows
    ]
    return JsonResponse({
        "width": pmap.width, "height": pmap.height,
        "grid": {"cols": pmap.grid_cols, "rows": pmap.grid_rows,
                 "visible": pmap.grid_visible},
        "beds": beds, "points": points, "layers": layers,
    })


@login_required
def bed_detail(request, pk):
    """Bed-focused map and its accessible, coordinated plant list."""
    g = garden_for(request)
    bed = get_object_or_404(
        Bed.objects.select_related("bed_type"),
        pk=pk,
        garden=g,
        archived_at__isnull=True,
    )
    locations = list(
        bed.plant_locations.filter(is_current=True, plant__status="active")
        .select_related("plant", "plant__primary_photo")
        .order_by("plant__common_name", "plant__cultivar", "pk")
    )
    pmap = PropertyMap.get(g)
    active_master = MapLayer.objects.filter(
        garden=g,
        kind=MapLayerKind.MASTER,
        is_primary=True,
        archived_at__isnull=True,
    ).first()
    return render(request, "garden/beds/detail.html", {
        "nav": "map",
        "bed": bed,
        "locations": locations,
        "mapped_count": sum(
            loc.point_x is not None and loc.point_y is not None for loc in locations
        ),
        "grid_cells": pmap.cells_for_polygon(bed.boundary or []),
        "active_master": active_master,
    })


@require_POST
@login_required
def bed_boundary(request, pk):
    """Save a traced bed polygon: JSON body {"boundary": [[x,y], ...] | null}."""
    g = garden_for(request)
    bed = get_object_or_404(Bed, pk=pk, garden=g, archived_at__isnull=True)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "That outline could not be read."}, status=400)
    boundary = _boundary_from_payload(payload)
    if boundary is None:
        return JsonResponse({"error": "boundary must be [[x,y],...] with 3+ points"}, status=400)
    bed.boundary = boundary
    bed.save(update_fields=["boundary"])
    cells = PropertyMap.get(g).cells_for_polygon(boundary or [])
    return JsonResponse({"ok": True, "cells": cells})


@require_POST
@login_required
def bed_create_from_outline(request):
    """Create and name a bed after its polygon has been traced on the map."""
    g = garden_for(request)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "That outline could not be read."}, status=400)

    name = payload.get("name", "")
    name = name.strip() if isinstance(name, str) else ""
    if not name:
        return JsonResponse({"error": "Give the garden bed a name."}, status=400)
    if len(name) > Bed._meta.get_field("name").max_length:
        return JsonResponse({"error": "Keep the bed name under 100 characters."}, status=400)
    boundary = _boundary_from_payload(payload)
    if boundary is None:
        return JsonResponse({"error": "Tap at least three points to outline the bed."}, status=400)
    if Bed.objects.filter(
        garden=g, archived_at__isnull=True, name__iexact=name
    ).exists():
        return JsonResponse(
            {"error": "There is already an active bed with that name."}, status=409
        )

    try:
        bed = Bed.objects.create(garden=g, name=name, boundary=boundary)
    except IntegrityError:
        return JsonResponse(
            {"error": "There is already an active bed with that name."}, status=409
        )
    return JsonResponse(
        {
            "ok": True,
            "bed": {
                "id": bed.pk,
                "code": bed.code,
                "name": bed.name,
                "url": reverse("bed-detail", args=[bed.pk]),
            },
            "cells": PropertyMap.get(g).cells_for_polygon(boundary),
        },
        status=201,
    )


def _layer_canvas_box(pmap, layer):
    """Return a layer's map-space (x, y, width, height), preserving its ratio."""
    if layer.canvas_width and layer.canvas_height:
        return (
            layer.canvas_x or 0,
            layer.canvas_y or 0,
            layer.canvas_width,
            layer.canvas_height,
        )
    if layer.natural_width and layer.natural_height:
        scale = min(pmap.width / layer.natural_width, pmap.height / layer.natural_height)
        width = layer.natural_width * scale
        height = layer.natural_height * scale
        return ((pmap.width - width) / 2, (pmap.height - height) / 2, width, height)
    return (0, 0, pmap.width, pmap.height)


@require_POST
@login_required
def bed_suggest_outline(request):
    """Suggest, but never save, a bed polygon from a selected map region."""
    g = garden_for(request)
    try:
        payload = json.loads(request.body)
        bounds = payload["bounds"]
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or not all(
                isinstance(point, list)
                and len(point) == 2
                and all(isinstance(value, int | float) for value in point)
                for point in bounds
            )
        ):
            raise ValueError
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Select a rectangular map region first."}, status=400)

    if not ai.enabled():
        return JsonResponse(
            {"error": "AI outlining is unavailable; adjust the selected rectangle manually."},
            status=503,
        )

    layer = (
        MapLayer.objects.filter(
            garden=g,
            kind=MapLayerKind.MASTER,
            is_primary=True,
            archived_at__isnull=True,
        ).first()
        or MapLayer.objects.filter(
            garden=g,
            visible=True,
            archived_at__isnull=True,
        ).order_by("-is_primary", "-uploaded_at").first()
    )
    if layer is None:
        return JsonResponse(
            {"error": "Add a property map or reference image before requesting an outline."},
            status=409,
        )

    pmap = PropertyMap.get(g)
    layer_x, layer_y, layer_w, layer_h = _layer_canvas_box(pmap, layer)
    left, right = sorted((float(bounds[0][0]), float(bounds[1][0])))
    top, bottom = sorted((float(bounds[0][1]), float(bounds[1][1])))
    left, right = max(left, layer_x), min(right, layer_x + layer_w)
    top, bottom = max(top, layer_y), min(bottom, layer_y + layer_h)
    if right - left < 10 or bottom - top < 10:
        return JsonResponse(
            {"error": "Select a larger region that overlaps the property map."}, status=400
        )

    from PIL import Image as PILImage
    from PIL import UnidentifiedImageError

    try:
        with layer.image.open("rb") as source:
            image = PILImage.open(source)
            image.load()
        sx = image.width / layer_w
        sy = image.height / layer_h
        crop_box = (
            max(0, round((left - layer_x) * sx)),
            max(0, round((top - layer_y) * sy)),
            min(image.width, round((right - layer_x) * sx)),
            min(image.height, round((bottom - layer_y) * sy)),
        )
        crop = image.crop(crop_box).convert("RGB")
        encoded = io.BytesIO()
        crop.save(encoded, "JPEG", quality=90)
        crop_width, crop_height = crop.size
        crop_file = ContentFile(encoded.getvalue(), name="selected-map-region.jpg")
    except (UnidentifiedImageError, OSError, ValueError):
        return JsonResponse({"error": "The selected map image could not be read."}, status=400)

    try:
        suggestion = ai.suggest_bed_outline(
            crop_file,
            crop_width,
            crop_height,
            list(Bed.objects.filter(garden=g).values_list("name", flat=True)),
        )
    except ai.AIError:
        return JsonResponse(
            {"error": "No clear bed edge was found. Adjust the rectangle manually."},
            status=422,
        )

    boundary = [
        [
            round(left + point[0] / crop_width * (right - left)),
            round(top + point[1] / crop_height * (bottom - top)),
        ]
        for point in suggestion["boundary"]
    ]
    return JsonResponse({
        "ok": True,
        "boundary": boundary,
        "suggested_name": suggestion["suggested_name"],
        "confidence": suggestion["confidence"],
    })


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
    if MapLayer.objects.filter(
        garden=garden, kind=MapLayerKind.MASTER, is_primary=True,
        archived_at__isnull=True,
    ).exists():
        layer.is_primary = False
        layer.visible = False
        layer.save(update_fields=["is_primary", "visible"])
        return False

    others = MapLayer.objects.filter(
        garden=garden, archived_at__isnull=True
    ).exclude(kind=MapLayerKind.MASTER).exclude(pk=layer.pk)
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
    from PIL import UnidentifiedImageError

    g = garden_for(request)
    image = request.FILES.get("image")
    if image is None:
        return _map_error(request, "Choose a photo to use for the map.")
    try:
        with PILImage.open(image) as uploaded:
            natural_width, natural_height = float(uploaded.width), float(uploaded.height)
        image.seek(0)
    except (UnidentifiedImageError, OSError):
        return _map_error(
            request,
            "That photo format could not be read. In Photos, export it as "
            "JPEG or PNG and try again.",
        )
    name = request.POST.get("name") or image.name
    layer = MapLayer.objects.create(
        name=name,
        image=image,
        garden=g,
        kind=MapLayerKind.AERIAL,
        natural_width=natural_width,
        natural_height=natural_height,
    )
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
                     kind=MapLayerKind.AERIAL,
                     natural_width=1280.0, natural_height=1280.0)
    layer.image.save("satellite.png", ContentFile(image_bytes), save=True)
    _promote_layer(g, layer)
    _maybe_resize_space(g, layer)
    return redirect("map")


def _map_error(request, msg):
    g = garden_for(request)
    pmap = PropertyMap.get(g)
    masters = MapLayer.objects.filter(
        garden=g, kind=MapLayerKind.MASTER, archived_at__isnull=True
    )
    return render(request, "garden/map/map.html", {
        "nav": "map", "pmap": pmap, "error": msg,
        "layers": MapLayer.objects.filter(garden=g, archived_at__isnull=True),
        "active_master": masters.filter(is_primary=True).first(),
        "master_versions": masters.order_by("-version"),
        "bundled_master_installed": masters.filter(source_sha256=MASTER_MAP_SHA256).exists(),
        "reference_layers": MapLayer.objects.filter(
            garden=g, archived_at__isnull=True
        ).exclude(kind=MapLayerKind.MASTER),
        "focus_plant": "", "focus_bed": "",
        "beds": Bed.objects.filter(garden=g, archived_at__isnull=True),
        "plants": Plant.objects.filter(garden=g, status="active"),
    })


def _image_dimensions(upload):
    from PIL import Image as PILImage
    from PIL import UnidentifiedImageError

    try:
        with PILImage.open(upload) as opened:
            size = float(opened.width), float(opened.height)
        upload.seek(0)
        return size
    except (UnidentifiedImageError, OSError):
        return None


def _next_master_version(garden):
    latest = MapLayer.objects.filter(
        garden=garden, kind=MapLayerKind.MASTER
    ).aggregate(latest=Max("version"))["latest"]
    return (latest or 0) + 1


def _fit_master_to_canvas(pmap, layer):
    scale = min(pmap.width / layer.natural_width, pmap.height / layer.natural_height)
    width = layer.natural_width * scale
    height = layer.natural_height * scale
    layer.canvas_x = (pmap.width - width) / 2
    layer.canvas_y = (pmap.height - height) / 2
    layer.canvas_width = width
    layer.canvas_height = height


@transaction.atomic
def _activate_master(garden, layer):
    MapLayer.objects.filter(
        garden=garden, kind=MapLayerKind.MASTER, archived_at__isnull=True
    ).exclude(pk=layer.pk).update(is_primary=False, visible=False)

    pmap = PropertyMap.get(garden)
    if not _map_has_geometry(garden):
        pmap.width = layer.natural_width
        pmap.height = layer.natural_height
    # The master defines the clean default. Grid/record geometry remains in
    # the same permanent coordinate space and is revealed interactively.
    pmap.grid_visible = False
    pmap.save(update_fields=["width", "height", "grid_visible"])

    _fit_master_to_canvas(pmap, layer)
    layer.is_primary = True
    layer.visible = True
    layer.opacity = 1.0
    layer.save(update_fields=[
        "canvas_x", "canvas_y", "canvas_width", "canvas_height",
        "is_primary", "visible", "opacity",
    ])

    # Aerials remain available but never displace or obscure the clean master
    # until the user explicitly turns one on.
    MapLayer.objects.filter(garden=garden).exclude(kind=MapLayerKind.MASTER).update(
        is_primary=False, visible=False
    )


@require_POST
@login_required
def adopt_preserved_master(request):
    """Adopt the repository's byte-for-byte preserved PNW Home master."""
    g = garden_for(request)
    source = MASTER_MAP_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != MASTER_MAP_SHA256:
        return _map_error(request, "The preserved master map failed its integrity check.")

    existing = MapLayer.objects.filter(
        garden=g, kind=MapLayerKind.MASTER, source_sha256=MASTER_MAP_SHA256
    ).first()
    if existing:
        _activate_master(g, existing)
        return redirect("map")

    previous = MapLayer.objects.filter(
        garden=g, kind=MapLayerKind.MASTER, archived_at__isnull=True
    ).order_by("-version").first()
    layer = MapLayer(
        garden=g,
        name="Master Property Map",
        kind=MapLayerKind.MASTER,
        version=_next_master_version(g),
        source_sha256=MASTER_MAP_SHA256,
        immutable_original=True,
        supersedes=previous,
        natural_width=1072.0,
        natural_height=1244.0,
    )
    layer.image.save(MASTER_MAP_FILENAME, ContentFile(source), save=False)
    layer.save()
    _activate_master(g, layer)
    return redirect("map")


@require_POST
@login_required
def master_map_upload(request):
    """Create and activate a new immutable master version; never overwrite."""
    g = garden_for(request)
    image = request.FILES.get("image")
    if image is None:
        return _map_error(request, "Choose a revised property map to adopt.")
    dimensions = _image_dimensions(image)
    if dimensions is None:
        return _map_error(request, "That revised map could not be read as an image.")

    digest = hashlib.sha256()
    for chunk in image.chunks():
        digest.update(chunk)
    image.seek(0)
    previous = MapLayer.objects.filter(
        garden=g, kind=MapLayerKind.MASTER, archived_at__isnull=True
    ).order_by("-version").first()
    version = _next_master_version(g)
    layer = MapLayer.objects.create(
        garden=g,
        name=request.POST.get("name", "").strip() or f"Master Property Map v{version}",
        image=image,
        kind=MapLayerKind.MASTER,
        version=version,
        source_sha256=digest.hexdigest(),
        immutable_original=True,
        supersedes=previous,
        natural_width=dimensions[0],
        natural_height=dimensions[1],
    )
    _activate_master(g, layer)
    return redirect("map")


@require_POST
@login_required
def master_map_activate(request, pk):
    g = garden_for(request)
    layer = get_object_or_404(
        MapLayer,
        pk=pk,
        garden=g,
        kind=MapLayerKind.MASTER,
        archived_at__isnull=True,
    )
    _activate_master(g, layer)
    return redirect("map")


@require_POST
@login_required
def reference_layer_toggle(request, pk):
    g = garden_for(request)
    layer = get_object_or_404(
        MapLayer, pk=pk, garden=g, archived_at__isnull=True
    )
    if layer.kind != MapLayerKind.MASTER:
        layer.visible = not layer.visible
        layer.save(update_fields=["visible"])
    return redirect("map")
