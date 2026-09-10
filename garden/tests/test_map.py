import hashlib
import json

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

from garden.models import Bed, MapLayer, MapLayerKind, Plant, PlantLocation, PropertyMap

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_client(client):
    client.force_login(User.objects.create_user("m"))
    return client


def test_grid_cell_math():
    pmap = PropertyMap.get()  # 1000x750, 40x32 default
    assert pmap.cell_for(0, 0) == "A1"
    assert pmap.cell_for(999, 749) == "AN32"
    assert pmap.cell_for(450, 400) == "S18"
    assert pmap.cell_for(2000, 0) == ""  # out of bounds


def test_polygon_cells_err_toward_inclusion():
    pmap = PropertyMap.get()
    cells = pmap.cells_for_polygon([[50, 50], [250, 50], [250, 140], [50, 140]])
    assert "C3" in cells and "K6" in cells


def test_trace_bed_boundary_and_reject_bad_input(user_client):
    bed = Bed.objects.create(name="Front Bed")
    url = reverse("map-bed-boundary", args=[bed.pk])
    r = user_client.post(url, json.dumps({"boundary": [[0, 0], [100, 0], [100, 100]]}),
                         content_type="application/json")
    assert r.status_code == 200 and r.json()["ok"]
    bed.refresh_from_db()
    assert len(bed.boundary) == 3
    r = user_client.post(url, json.dumps({"boundary": [[0, 0]]}),
                         content_type="application/json")
    assert r.status_code == 400


def test_create_and_name_bed_from_map_outline(user_client):
    response = user_client.post(
        reverse("map-bed-create"),
        json.dumps({
            "name": "  Front rose bed  ",
            "boundary": [[10, 10], [110, 10], [110, 80], [10, 80]],
        }),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    bed = Bed.objects.get()
    assert body["ok"] and body["bed"] == {
        "id": bed.pk,
        "code": "BED-001",
        "name": "Front rose bed",
        "url": reverse("bed-detail", args=[bed.pk]),
    }
    assert bed.boundary == [[10, 10], [110, 10], [110, 80], [10, 80]]
    assert bed.garden.owner.username == "m"
    assert body["cells"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"name": "", "boundary": [[0, 0], [1, 0], [1, 1]]}, "Give the garden bed"),
        ({"name": "New bed", "boundary": [[0, 0], [1, 0]]}, "at least three points"),
    ],
)
def test_create_bed_from_map_rejects_incomplete_input(user_client, payload, message):
    response = user_client.post(
        reverse("map-bed-create"), json.dumps(payload), content_type="application/json"
    )

    assert response.status_code == 400
    assert message in response.json()["error"]
    assert not Bed.objects.exists()


def test_create_bed_from_map_rejects_duplicate_active_name(user_client):
    Bed.objects.create(name="Kitchen garden")

    response = user_client.post(
        reverse("map-bed-create"),
        json.dumps({"name": "kitchen GARDEN", "boundary": [[0, 0], [1, 0], [1, 1]]}),
        content_type="application/json",
    )

    assert response.status_code == 409
    assert Bed.objects.count() == 1


def test_place_plant_resolves_containing_bed(user_client):
    bed = Bed.objects.create(name="Front Bed",
                             boundary=[[0, 0], [200, 0], [200, 200], [0, 200]])
    plant = Plant.objects.create(common_name="Rose")
    r = user_client.post(reverse("map-plant-point", args=[plant.pk]),
                         json.dumps({"x": 100, "y": 100}),
                         content_type="application/json")
    body = r.json()
    assert body["ok"] and body["bed"] == "Front Bed"
    loc = plant.current_locations.get()
    assert (loc.point_x, loc.point_y) == (100, 100) and loc.bed == bed


def test_place_outside_any_bed_keeps_no_bed(user_client):
    Bed.objects.create(name="Front Bed", boundary=[[0, 0], [10, 0], [10, 10], [0, 10]])
    plant = Plant.objects.create(common_name="Oak")
    r = user_client.post(reverse("map-plant-point", args=[plant.pk]),
                         json.dumps({"x": 500, "y": 500}),
                         content_type="application/json")
    assert r.json()["bed"] == ""


def test_map_data_payload(user_client):
    bed = Bed.objects.create(name="Front Bed", boundary=[[0, 0], [50, 0], [50, 50], [0, 50]])
    plant = Plant.objects.create(common_name="Rose")
    PlantLocation.objects.create(plant=plant, bed=bed, point_x=25, point_y=25)
    data = user_client.get(reverse("map-data")).json()
    assert data["beds"][0]["cells"][0] == "A1"
    assert data["beds"][0]["cells"][-1] == "C3"
    assert data["beds"][0]["url"] == reverse("bed-detail", args=[bed.pk])
    assert data["points"][0]["name"] == "Rose" and data["points"][0]["cell"] == "B2"
    assert data["points"][0]["bed_id"] == bed.pk
    assert data["points"][0]["url"] == reverse("plant-detail", args=[plant.pk])


def test_bed_detail_has_focused_map_and_coordinated_plant_sidebar(user_client):
    bed = Bed.objects.create(
        name="Front Bed",
        short_code="FB",
        boundary=[[0, 0], [200, 0], [200, 200], [0, 200]],
    )
    rose = Plant.objects.create(common_name="Rose", cultivar="Peace")
    mapped = PlantLocation.objects.create(
        plant=rose, bed=bed, point_x=50, point_y=75, location_note="path edge"
    )
    fern = Plant.objects.create(common_name="Fern")
    PlantLocation.objects.create(plant=fern, bed=bed)

    response = user_client.get(reverse("bed-detail", args=[bed.pk]))

    assert response.status_code == 200
    assert b"Interactive map of Front Bed" in response.content
    assert b"Rose &#x27;Peace&#x27;" in response.content
    assert f'data-plant-location="{mapped.pk}"'.encode() in response.content
    assert b"path edge" in response.content
    assert b"Located on map" in response.content
    assert b"Not placed on map" in response.content
    assert b"Hover over a plant dot" in response.content
    assert b"1 of 2 plant locations placed on the map" in response.content
    assert b'focusBed: "' + str(bed.pk).encode() + b'"' in response.content


def test_bed_detail_without_outline_offers_property_map(user_client):
    bed = Bed.objects.create(name="New Bed")

    response = user_client.get(reverse("bed-detail", args=[bed.pk]))

    assert response.status_code == 200
    assert b"This bed is not outlined yet" in response.content
    assert reverse("map").encode() + f"?bed={bed.pk}".encode() in response.content
    assert b"yardwise-map.js" not in response.content


def test_map_page_renders_with_focus(user_client):
    plant = Plant.objects.create(common_name="Rose")
    r = user_client.get(reverse("map"), {"plant": plant.pk})
    assert r.status_code == 200
    assert b"yardwise-map.js" in r.content
    assert b"Outline a new bed" in r.content
    assert b"Drag a photo here" in r.content
    assert b"choose from Photos or files" in r.content
    assert b"Master Property Map" in r.content
    assert b"Use the preserved Master Property Map" in r.content


def test_bed_list_opens_profile_instead_of_edit_form(user_client):
    bed = Bed.objects.create(name="Front Bed")

    response = user_client.get(reverse("bed-list"))

    assert reverse("bed-detail", args=[bed.pk]).encode() in response.content
    assert reverse("bed-edit", args=[bed.pk]).encode() not in response.content


def test_preserved_master_asset_is_exact_and_adopts_locked(user_client):
    from garden.views_map import MASTER_MAP_PATH, MASTER_MAP_SHA256

    source = MASTER_MAP_PATH.read_bytes()
    assert hashlib.sha256(source).hexdigest() == MASTER_MAP_SHA256

    response = user_client.post(reverse("map-master-adopt-preserved"))

    assert response.status_code == 302
    layer = MapLayer.objects.get(kind=MapLayerKind.MASTER)
    assert layer.name == "Master Property Map"
    assert layer.version == 1
    assert layer.is_primary and layer.visible and layer.immutable_original
    assert layer.source_sha256 == MASTER_MAP_SHA256
    assert (layer.natural_width, layer.natural_height) == (1072.0, 1244.0)
    with layer.image.open("rb") as installed:
        assert installed.read() == source
    pmap = _pmap(user_client)
    assert (pmap.width, pmap.height) == (1072.0, 1244.0)
    assert not pmap.grid_visible


def test_master_adoption_preserves_existing_geometry(user_client):
    pmap = _pmap(user_client)
    pmap.width, pmap.height = 1280, 900
    pmap.save(update_fields=["width", "height"])
    bed = Bed.objects.create(
        name="Existing bed", boundary=[[100, 100], [300, 100], [300, 300]]
    )
    plant = Plant.objects.create(common_name="Existing rose")
    location = PlantLocation.objects.create(plant=plant, point_x=175, point_y=220)

    user_client.post(reverse("map-master-adopt-preserved"))

    pmap.refresh_from_db()
    bed.refresh_from_db()
    location.refresh_from_db()
    assert (pmap.width, pmap.height) == (1280, 900)
    assert bed.boundary == [[100, 100], [300, 100], [300, 300]]
    assert (location.point_x, location.point_y) == (175, 220)
    master = MapLayer.objects.get(kind=MapLayerKind.MASTER)
    assert master.canvas_width <= pmap.width
    assert master.canvas_height <= pmap.height


def test_future_master_is_new_version_without_moving_geometry(user_client):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    user_client.post(reverse("map-master-adopt-preserved"))
    first = MapLayer.objects.get(kind=MapLayerKind.MASTER)
    Bed.objects.create(name="Pinned", boundary=[[10, 10], [20, 10], [20, 20]])
    before = (_pmap(user_client).width, _pmap(user_client).height)
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(buf, "PNG")

    response = user_client.post(reverse("map-master-upload"), {
        "name": "Paths revised",
        "image": SimpleUploadedFile("revision.png", buf.getvalue(), "image/png"),
    })

    assert response.status_code == 302
    first.refresh_from_db()
    second = MapLayer.objects.get(kind=MapLayerKind.MASTER, version=2)
    assert second.is_primary and second.visible and second.immutable_original
    assert second.supersedes == first
    assert not first.is_primary and not first.visible
    assert (_pmap(user_client).width, _pmap(user_client).height) == before

    response = user_client.post(reverse("map-master-activate", args=[first.pk]))
    assert response.status_code == 302
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary and first.visible
    assert not second.is_primary and not second.visible
    assert (_pmap(user_client).width, _pmap(user_client).height) == before


def test_locked_master_source_cannot_be_overwritten(user_client):
    user_client.post(reverse("map-master-adopt-preserved"))
    layer = MapLayer.objects.get(kind=MapLayerKind.MASTER)
    layer.image = "map/replacement.png"

    with pytest.raises(ValidationError, match="cannot be overwritten"):
        layer.save()


def test_aerial_added_after_master_stays_hidden_reference(user_client):
    user_client.post(reverse("map-master-adopt-preserved"))

    _upload_png(user_client, "historical aerial", 640, 480)

    master = MapLayer.objects.get(kind=MapLayerKind.MASTER)
    aerial = MapLayer.objects.get(kind=MapLayerKind.AERIAL)
    assert master.is_primary and master.visible
    assert not aerial.is_primary and not aerial.visible


def test_map_data_identifies_master_and_uses_fixed_canvas_bounds(user_client):
    user_client.post(reverse("map-master-adopt-preserved"))

    data = user_client.get(reverse("map-data")).json()

    master = data["layers"][0]
    assert master["kind"] == "master" and master["version"] == 1
    assert master["render_w"] == 1072.0 and master["render_h"] == 1244.0


def test_master_and_reference_actions_are_post_only_and_garden_scoped(user_client):
    from garden.models import Garden

    other_owner = User.objects.create_user("other")
    other_garden = Garden.for_user(other_owner)
    other_master = MapLayer.objects.create(
        garden=other_garden,
        name="Other master",
        image="map/other.png",
        kind=MapLayerKind.MASTER,
        version=1,
        is_primary=True,
    )
    other_reference = MapLayer.objects.create(
        garden=other_garden,
        name="Other aerial",
        image="map/other-aerial.png",
        kind=MapLayerKind.AERIAL,
    )

    assert user_client.get(reverse("map-master-adopt-preserved")).status_code == 405
    assert user_client.post(
        reverse("map-master-activate", args=[other_master.pk])
    ).status_code == 404
    assert user_client.post(
        reverse("map-layer-toggle", args=[other_reference.pk])
    ).status_code == 404


def test_map_photo_upload_without_image_shows_friendly_error(user_client):
    response = user_client.post(reverse("map-layer-upload"), {"name": "Nothing"})

    assert response.status_code == 200
    assert b"Choose a photo to use for the map" in response.content


def test_map_photo_upload_rejects_unreadable_format(user_client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    response = user_client.post(
        reverse("map-layer-upload"),
        {"image": SimpleUploadedFile("not-a-photo.heic", b"not really an image", "image/heic")},
    )

    assert response.status_code == 200
    assert b"export it as JPEG or PNG" in response.content


def test_satellite_fetch_geocodes_and_creates_layer(user_client, monkeypatch, settings, tmp_path):

    settings.MEDIA_ROOT = str(tmp_path)
    calls = []

    class FakeResp:
        def __init__(self, payload):
            self.payload = payload
        def read(self):
            return self.payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        url = req if isinstance(req, str) else req.full_url
        calls.append(url)
        if "nominatim" in url:
            return FakeResp(b'[{"lat": "47.6", "lon": "-122.3"}]')
        return FakeResp(b"\x89PNG fake image bytes")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    r = user_client.post(reverse("map-satellite"), {"address": "123 Main St", "span_m": "150"})
    assert r.status_code == 302
    from garden.models import MapLayer
    layer = MapLayer.objects.get()
    assert layer.is_primary and "123 Main St" in layer.name
    assert _pmap(user_client).width == 1280.0
    assert any("nominatim" in u for u in calls) and any("World_Imagery" in u for u in calls)


def test_satellite_fetch_no_match_shows_error(user_client, monkeypatch):
    import urllib.request

    class FakeResp:
        def read(self):
            return b"[]"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    r = user_client.post(reverse("map-satellite"), {"address": "zzz nowhere"})
    assert r.status_code == 200 and b"Couldn&#x27;t find" in r.content


def test_geocode_prefers_census_result(monkeypatch):
    import garden.views_map as vm

    class FakeResp:
        def __init__(self, payload):
            self.payload = payload
        def read(self):
            return self.payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        url = req.full_url
        if "census" in url:
            return FakeResp(
                b'{"result": {"addressMatches": [{"coordinates": {"x": "-122.3", "y": "47.6"}}]}}'
            )
        raise AssertionError("nominatim should not be called when census matches")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert vm._geocode("123 Main St, Yakima, WA 98901") == (47.6, -122.3)


def test_media_served_to_logged_in_users_only(user_client, client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    default_storage.save("photos/x.png", ContentFile(b"\x89PNG fake"))
    r = user_client.get("/media/photos/x.png")
    assert r.status_code == 200
    from django.test import Client

    anon = Client()
    r = anon.get("/media/photos/x.png")
    assert r.status_code == 302  # bounced to login, never the file


def test_newest_layer_replaces_previous_as_primary(user_client):
    from garden.models import MapLayer

    def upload(name):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "green").save(buf, "PNG")
        return user_client.post(
            reverse("map-layer-upload"),
            {"image": SimpleUploadedFile(f"{name}.png", buf.getvalue(), "image/png"),
             "name": name},
        )

    upload("satellite-ish")
    first = MapLayer.objects.get()
    assert first.is_primary and first.visible

    upload("my own aerial")
    first.refresh_from_db()
    second = MapLayer.objects.get(name="my own aerial")
    assert second.is_primary and second.visible  # newest wins
    assert not first.is_primary and not first.visible  # old kept, hidden
    # with no geometry, the space follows the newest image's shape
    assert _pmap(user_client).width == 10.0




def _pmap(client):
    """The PropertyMap row belonging to the logged-in test user's garden."""
    from django.contrib.auth.models import User

    from garden.models import PropertyMap
    from garden.models.tenancy import Garden

    return PropertyMap.get(Garden.for_user(User.objects.get(username="m")))


def _upload_png(user_client, name, w, h):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (w, h), "green").save(buf, "PNG")
    return user_client.post(
        reverse("map-layer-upload"),
        {"image": SimpleUploadedFile(f"{name}.png", buf.getvalue(), "image/png"), "name": name},
    )


def test_layer_records_natural_size_and_resizes_empty_space(user_client):
    from garden.models import MapLayer

    _upload_png(user_client, "wide", 30, 20)
    layer = MapLayer.objects.get()
    assert (layer.natural_width, layer.natural_height) == (30.0, 20.0)
    # no geometry yet -> space adopts the image's shape
    assert (_pmap(user_client).width, _pmap(user_client).height) == (30.0, 20.0)
    # a second image, different shape, still no geometry -> space follows again
    _upload_png(user_client, "tall", 10, 40)
    assert (_pmap(user_client).width, _pmap(user_client).height) == (10.0, 40.0)


def test_space_frozen_once_geometry_exists(user_client):
    _upload_png(user_client, "first", 30, 20)
    Bed.objects.create(name="Traced", boundary=[[0, 0], [5, 0], [5, 5]])
    _upload_png(user_client, "second", 100, 10)
    # traced data pins the space; the new image will letterbox client-side
    assert (_pmap(user_client).width, _pmap(user_client).height) == (30.0, 20.0)


def test_map_data_includes_layer_dims(user_client):
    _upload_png(user_client, "wide", 30, 20)
    data = user_client.get(reverse("map-data")).json()
    assert data["layers"][0]["w"] == 30.0 and data["layers"][0]["h"] == 20.0


def test_serve_media_streams_from_storage(user_client, settings, tmp_path):
    # storage-agnostic serve: write via the storage API (not the filesystem
    # path) and stream back through /media/
    settings.MEDIA_ROOT = str(tmp_path)
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    default_storage.save("photos/streamed.png", ContentFile(b"\x89PNG streamed"))
    r = user_client.get("/media/photos/streamed.png")
    assert r.status_code == 200
    assert r["Content-Type"] == "image/png"
    assert b"".join(r.streaming_content) == b"\x89PNG streamed"
    assert user_client.get("/media/photos/missing.png").status_code == 404
