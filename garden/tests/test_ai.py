
import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden import ai
from garden.models import AISuggestion, Plant, ProblemCase

pytestmark = pytest.mark.django_db


@pytest.fixture
def user_client(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client.force_login(User.objects.create_user("m"))
    return client


def _png():
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buf, "PNG")
    return SimpleUploadedFile("x.png", buf.getvalue(), "image/png")


def test_ai_routes_hidden_without_key(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client.force_login(User.objects.create_user("m"))
    assert client.get(reverse("ai-identify")).status_code == 404
    assert client.get(reverse("ai-ask")).status_code == 404


def test_identify_creates_suggestion_not_records(user_client, monkeypatch):
    monkeypatch.setattr(ai, "identify", lambda *a, **k: {
        "name": "Bindweed", "scientific_name": "Convolvulus arvensis", "kind": "weed",
        "confidence": "high", "summary": "A twining weed.", "action_advice": "Dig it out.",
        "caution": "",
    })
    r = user_client.post(reverse("ai-identify"), {"photo": _png(), "question": "weed?"})
    assert r.status_code == 302
    s = AISuggestion.objects.get()
    assert s.status == "pending"
    assert ProblemCase.objects.count() == 0  # nothing created until accepted


def test_accepting_identification_creates_problem_case(user_client, monkeypatch):
    monkeypatch.setattr(ai, "identify", lambda *a, **k: {
        "name": "Aphids", "kind": "pest", "confidence": "medium",
        "summary": "Sap suckers.", "action_advice": "Blast with water.", "caution": "",
    })
    user_client.post(reverse("ai-identify"), {"photo": _png()})
    s = AISuggestion.objects.get()
    r = user_client.post(reverse("ai-suggestion", args=[s.pk]), {"action": "problem"})
    assert r.status_code == 302
    case = ProblemCase.objects.get()
    assert case.problem_type.name == "Aphids" and case.photos.count() == 1
    s.refresh_from_db()
    assert s.status == "accepted"


def test_enrichment_fills_only_empty_and_selected_fields(user_client, monkeypatch):
    plant = Plant.objects.create(common_name="Blueberry", sun="full")  # sun populated
    monkeypatch.setattr(ai, "enrich", lambda *a, **k: {
        "water_needs": "moderate", "mature_height": "4-6 ft",
    })
    r = user_client.post(reverse("plant-enrich", args=[plant.pk]))
    assert b"4-6 ft" in r.content  # review screen
    s = AISuggestion.objects.get(kind="enrich")
    # accept only water_needs
    user_client.post(reverse("plant-enrich", args=[plant.pk]), {
        "apply": "1", "suggestion": s.pk, "accept_water_needs": "on",
    })
    plant.refresh_from_db()
    assert plant.water_needs == "moderate"
    assert plant.mature_height == ""  # not selected
    assert plant.sun == "full"  # untouched
    s.refresh_from_db()
    assert s.accepted_fields == ["water_needs"]


def test_enrich_choice_constraints_exist():
    from garden.ai import CHOICE_FIELDS
    assert "part" in CHOICE_FIELDS["sun"]


def test_ask_records_question(user_client, monkeypatch):
    Plant.objects.create(common_name="Pear")
    monkeypatch.setattr(ai, "ask", lambda *a, **k: "Prune the pear in late winter.")
    r = user_client.post(reverse("ai-ask"), {"question": "what should I prune?"})
    assert b"late winter" in r.content
    assert AISuggestion.objects.filter(kind="question").count() == 1


def test_low_confidence_warning_shown(user_client, monkeypatch):
    monkeypatch.setattr(ai, "identify", lambda *a, **k: {
        "name": "Maybe nightshade", "kind": "weed", "confidence": "low",
        "summary": "Hard to tell.", "action_advice": "Get a closer photo.",
        "caution": "Toxic lookalikes.",
    })
    user_client.post(reverse("ai-identify"), {"photo": _png()})
    s = AISuggestion.objects.get()
    r = user_client.get(reverse("ai-suggestion", args=[s.pk]))
    assert b"Low confidence" in r.content and b"Toxic lookalikes" in r.content
