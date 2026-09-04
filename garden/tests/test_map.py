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
    from garden.models import MapLayer, PropertyMap
    layer = MapLayer.objects.get()
    assert layer.is_primary and "123 Main St" in layer.name
    assert PropertyMap.get().width == 1280.0
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
