import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden.models import Bed, Plant, PlantLocation, PropertyMap

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_client(client):
    client.force_login(User.objects.create_user("m"))
    return client


def test_grid_cell_math():
    pmap = PropertyMap.get()  # 1000x750, 10x8 default
    assert pmap.cell_for(0, 0) == "A1"
    assert pmap.cell_for(999, 749) == "J8"
    assert pmap.cell_for(450, 400) == "E5"
    assert pmap.cell_for(2000, 0) == ""  # out of bounds


def test_polygon_cells_err_toward_inclusion():
    pmap = PropertyMap.get()
    cells = pmap.cells_for_polygon([[50, 50], [250, 50], [250, 140], [50, 140]])
    assert "A1" in cells and "C2" in cells


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
        "id": bed.pk, "code": "BED-001", "name": "Front rose bed",
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
    assert data["beds"][0]["cells"] == ["A1"]
    assert data["points"][0]["name"] == "Rose" and data["points"][0]["cell"] == "A1"


def test_map_page_renders_with_focus(user_client):
    plant = Plant.objects.create(common_name="Rose")
    r = user_client.get(reverse("map"), {"plant": plant.pk})
    assert r.status_code == 200
    assert b"yardwise-map.js" in r.content
    assert b"Outline a new bed" in r.content
    assert b"Drag a photo here" in r.content
    assert b"choose from Photos or files" in r.content


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
    (tmp_path / "photos").mkdir()
    (tmp_path / "photos" / "x.png").write_bytes(b"\x89PNG fake")
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
