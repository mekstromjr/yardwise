
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
    assert client.get(reverse("assistant")).status_code == 404


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
        "spring_care": "Mulch after the soil warms.",
        "problems_to_watch": "Watch new growth for aphids.",
    })
    r = user_client.post(reverse("plant-enrich", args=[plant.pk]))
    assert b"4-6 ft" in r.content  # review screen
    s = AISuggestion.objects.get(kind="enrich")
    # accept only water_needs
    user_client.post(reverse("plant-enrich", args=[plant.pk]), {
        "apply": "1", "suggestion": s.pk, "accept_water_needs": "on",
        "accept_spring_care": "on", "accept_problems_to_watch": "on",
    })
    plant.refresh_from_db()
    assert plant.water_needs == "moderate"
    assert plant.mature_height == ""  # not selected
    assert plant.sun == "full"  # untouched
    assert plant.spring_care == "Mulch after the soil warms."
    assert plant.problems_to_watch == "Watch new growth for aphids."
    s.refresh_from_db()
    assert s.accepted_fields == ["water_needs", "spring_care", "problems_to_watch"]


def test_enrichment_requests_practical_care_and_preserves_existing_text(monkeypatch):
    plant = Plant(common_name="Blueberry", sun="full", spring_care="User's spring notes")
    captured = {}

    def fake_complete(messages, **kwargs):
        captured["messages"] = messages
        return ('{"spring_care": "Replace it", "summer_care": "Water deeply.", '
                '"pruning_recommendations": "Remove old canes in late winter.", '
                '"problems_to_watch": "Watch for mummy berry."}', [])

    monkeypatch.setattr(ai, "complete", fake_complete)
    proposed = ai.enrich(plant, region="Pacific Northwest")

    assert "spring_care" not in proposed
    assert proposed["summer_care"] == "Water deeply."
    assert "late winter" in proposed["pruning_recommendations"]
    assert proposed["problems_to_watch"] == "Watch for mummy berry."
    prompt = captured["messages"][0]["content"]
    assert "when and how to prune" in prompt
    assert "early signs" in prompt
    requested_fields = prompt.split("containing at most these keys:", 1)[1].split("Omit", 1)[0]
    assert "spring_care" not in requested_fields


def test_enrich_choice_constraints_exist():
    from garden.ai import CHOICE_FIELDS
    assert "part" in CHOICE_FIELDS["sun"]


def test_ask_records_question(user_client, monkeypatch):
    Plant.objects.create(common_name="Pear")
    monkeypatch.setattr(ai, "ask", lambda *a, **k: (
        "Prune the pear in late winter.",
        [{"title": "OSU Extension - pruning pears", "url": "https://example.edu/pears"}],
    ))
    r = user_client.post(reverse("assistant"), {"question": "what should I prune?"})
    assert b"late winter" in r.content
    assert b"OSU Extension" in r.content  # web citations rendered
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


# --- Plant lookup at creation ------------------------------------------------


def test_lookup_shows_candidates_and_prefills_form(user_client, monkeypatch):
    monkeypatch.setattr(ai, "lookup_plant", lambda *a, **k: [
        {"common_name": "Highbush Blueberry", "botanical_name": "Vaccinium corymbosum",
         "summary": "Classic garden blueberry.", "plant_type": "Shrub", "is_edible": True,
         "sun": "full", "water_needs": "moderate", "mature_height": "5-8 ft",
         "toxicity_notes": ""},
        {"common_name": "Lowbush Blueberry", "botanical_name": "Vaccinium angustifolium",
         "summary": "Wild type, groundcover habit.", "plant_type": "Shrub",
         "is_edible": True, "sun": "full", "water_needs": "moderate"},
    ])
    r = user_client.post(reverse("plant-lookup"), {"name": "blueberry"})
    assert b"Highbush Blueberry" in r.content and b"Lowbush" in r.content
    assert Plant.objects.count() == 0  # nothing created by searching
    # choose the first candidate -> redirected to Add Plant, pre-filled
    r = user_client.post(reverse("plant-lookup"), {"choose": "0", "name": "blueberry"})
    assert r.status_code == 302 and r.url.endswith("/plants/add/")
    r = user_client.get(reverse("plant-add"))
    assert b"Highbush Blueberry" in r.content and b"Vaccinium corymbosum" in r.content
    assert b"Details filled from lookup" in r.content
    # prefill is one-shot: a fresh visit is blank
    r = user_client.get(reverse("plant-add"))
    assert b"Highbush Blueberry" not in r.content


def test_lookup_hidden_without_key(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client.force_login(User.objects.create_user("x"))
    assert client.get(reverse("plant-lookup")).status_code == 404


def test_assistant_hub_lists_history_and_saved(user_client, monkeypatch):
    from garden.models import AISuggestion

    AISuggestion.objects.create(kind="question", question="When to plant peas?",
                                response={"answer": "Late winter."}, status="accepted")
    AISuggestion.objects.create(kind="identify", status="saved",
                                response={"name": "Mystery vine", "confidence": "low"})
    r = user_client.get(reverse("assistant"))
    assert b"When to plant peas?" in r.content
    assert b"Mystery vine" in r.content and b"Saved for later" in r.content


def test_web_plugin_sent_when_enabled(monkeypatch):
    import urllib.request

    captured = {}

    class FakeResp:
        def read(self):
            return (b'{"choices": [{"message": {"content": "hi", '
                    b'"annotations": [{"url_citation": {"url": "https://x.y", "title": "T"}}]}}]}')
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        import json as j
        captured.update(j.loads(req.data))
        return FakeResp()

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    from garden import ai as ai_mod

    content, sources = ai_mod.complete([{"role": "user", "content": "q"}], web=True)
    assert captured.get("plugins") == [{"id": "web"}]
    assert sources == [{"title": "T", "url": "https://x.y"}]
    # opt-out respected
    monkeypatch.setenv("YARDWISE_AI_WEB", "0")
    captured.clear()
    ai_mod.complete([{"role": "user", "content": "q"}], web=True)
    assert "plugins" not in captured


def test_identify_sends_web_derivative_not_original(user_client, monkeypatch):
    """A 48MP original base64-encoded is tens of MB in memory; the web
    derivative carries everything the model needs."""
    captured = {}

    def fake_identify(photo_file, *a, **k):
        captured["name"] = getattr(photo_file, "name", "")
        return {"name": "Fern", "kind": "plant", "confidence": "high",
                "summary": "s", "action_advice": "none needed", "caution": ""}

    monkeypatch.setattr(ai, "identify", fake_identify)
    user_client.post(reverse("ai-identify"), {"photo": _png(), "question": "?"})
    assert captured["name"].endswith("_web.jpg"), captured


def test_bed_outline_suggestion_is_bounded_and_uses_existing_names(monkeypatch):
    captured = {}

    def fake_complete(messages, **kwargs):
        captured["messages"] = messages
        return (
            '{"boundary": [[10, 10], [190, 10], [180, 90], [20, 90]], '
            '"suggested_name": "North fence bed", "confidence": "high"}',
            [],
        )

    monkeypatch.setattr(ai, "complete", fake_complete)
    result = ai.suggest_bed_outline(
        _png(),
        200,
        100,
        ["Rose Bed"],
        initial_boundary=[[12, 12], [188, 12], [180, 88], [20, 88]],
    )

    assert result["suggested_name"] == "North fence bed"
    assert result["confidence"] == "high"
    assert len(result["boundary"]) == ai.MIN_AI_BED_POINTS
    prompt = captured["messages"][0]["content"]
    assert "brown-to-path" in prompt and "fences" in prompt and "user will adjust" in prompt
    assert "direction change" in prompt
    assert "Rose Bed" in captured["messages"][1]["content"][0]["text"]
    assert "manual outline" in captured["messages"][1]["content"][0]["text"]


def test_bed_outline_densifies_long_edges_without_changing_shape(monkeypatch):
    monkeypatch.setattr(ai, "complete", lambda *args, **kwargs: (
        '{"boundary": [[0, 0], [100, 0], [100, 100], [0, 100]], '
        '"suggested_name": "Square bed", "confidence": "medium"}',
        [],
    ))

    result = ai.suggest_bed_outline(_png(), 100, 100, [])

    assert len(result["boundary"]) == ai.MIN_AI_BED_POINTS
    assert all(
        point[0] in (0, 100) or point[1] in (0, 100)
        for point in result["boundary"]
    )


def test_bed_outline_rejects_points_outside_selected_crop(monkeypatch):
    monkeypatch.setattr(ai, "complete", lambda *args, **kwargs: (
        '{"boundary": [[-1, 0], [100, 0], [100, 100], [0, 100]], '
        '"suggested_name": "Bed", "confidence": "medium"}',
        [],
    ))

    with pytest.raises(ai.AIError, match="outside"):
        ai.suggest_bed_outline(_png(), 100, 100, [])
