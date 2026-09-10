"""AI assistance (PDD section 9) via OpenRouter.

Canonical rules enforced here and in the views:
- AI is optional: no OPENROUTER_API_KEY -> features hidden, core app unchanged.
- AI output is a SUGGESTION until the user accepts it; nothing here writes to
  garden records.
- Enrichment proposes values for EMPTY fields only (PDD 9: fill missing by
  default, never replace populated fields).

stdlib urllib on purpose - no new dependency for one JSON endpoint.
"""

import base64
import json
import os
import urllib.error
import urllib.request

API_URL = "https://openrouter.ai/api/v1/chat/completions"


def enabled() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def model() -> str:
    return os.environ.get("YARDWISE_AI_MODEL", "google/gemini-2.5-flash")


def web_search_enabled() -> bool:
    """Ground answers with live web search (OpenRouter's web plugin). On by
    default so advice and safety claims cite current sources instead of
    leaning on training data alone; set YARDWISE_AI_WEB=0 to disable (each
    searched request adds a small cost on the OpenRouter key)."""
    return os.environ.get("YARDWISE_AI_WEB", "1").lower() not in ("0", "false", "no")


class AIError(Exception):
    """Raised for transport/parse failures; views translate to a calm message."""


def complete(messages: list[dict], json_mode: bool = False,
             web: bool = False) -> tuple[str, list[dict]]:
    """Returns (content, sources). Sources are OpenRouter url_citation
    annotations - [{"title": ..., "url": ...}] - present when the web plugin
    actually searched; empty otherwise."""
    payload = {"model": model(), "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if web and web_search_enabled():
        payload["plugins"] = [{"id": "web"}]
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read())
        message = body["choices"][0]["message"]
        sources = []
        for ann in message.get("annotations") or []:
            cite = ann.get("url_citation") or {}
            if cite.get("url"):
                sources.append({"title": cite.get("title") or cite["url"],
                                "url": cite["url"]})
        return message["content"], sources
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise AIError(str(exc)) from exc


def _image_part(django_file) -> dict:
    django_file.open("rb")
    data = base64.b64encode(django_file.read()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}


def identify(photo_file, question: str, region: str, context: str) -> dict:
    """Photo identification for 'Is this a weed?' / 'What is this pest?' /
    'What's wrong with this plant?'. Returns a dict with keys:
    name, scientific_name, kind (weed|pest|disease|plant|beneficial|unsure),
    confidence (low|medium|high), summary, action_advice, caution.
    """
    system = (
        "You identify plants, weeds, pests, and plant diseases from photos for a home "
        f"gardener in {region or 'the Pacific Northwest, USA'}. Be honest about "
        "uncertainty - a wrong confident answer is worse than 'unsure'. Never advise "
        "destroying anything on a low-confidence identification; note beneficial "
        "organisms as such. Respond ONLY with a JSON object with keys: name, "
        "scientific_name, kind (one of weed/pest/disease/plant/beneficial/unsure), "
        "confidence (low/medium/high), summary (2-3 sentences, plain language), "
        "action_advice (what to do and when, or 'none needed'), caution (safety/"
        "lookalike warnings, or empty string)."
    )
    user_content = [
        {"type": "text", "text": f"{question}\n\nGarden context: {context}"},
        _image_part(photo_file),
    ]
    raw, sources = complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
        json_mode=True, web=True,
    )
    try:
        out = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"unparseable identification: {raw[:200]}") from exc
    out.setdefault("kind", "unsure")
    out.setdefault("confidence", "low")
    out["sources"] = sources
    return out


def suggest_bed_outline(photo_file, width: int, height: int, existing_names: list[str]) -> dict:
    """Suggest a bed polygon within a user-selected map crop.

    The returned pixel coordinates are only a reviewable proposal. Saving the
    authoritative Bed boundary remains a separate, explicit user action.
    """
    system = (
        "You help a home gardener trace one garden bed in a selected crop of a property "
        "plan. Identify the most likely managed planting area in the crop. Brown or "
        "mulched areas often indicate garden beds; use visible paths, fences, building "
        "edges, retaining edges, and other structures to infer its boundary. Do not "
        "include paths, lawn, buildings, or neighboring beds. Return ONLY a JSON object "
        "with keys: boundary, suggested_name, confidence. boundary must be 4-16 [x,y] "
        f"points in clockwise order using crop pixels from [0,0] to [{width},{height}]. "
        "Use enough points for curved or irregular edges without excessive detail. "
        "suggested_name should be a short logical location-based name, not a guessed "
        "plant name. confidence must be low, medium, or high. If uncertain, still give "
        "the best conservative outline because the user will adjust it."
    )
    context = (
        "Existing bed names to avoid duplicating: " + ", ".join(existing_names)
        if existing_names else "There are no existing bed names."
    )
    raw, _sources = complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": context},
                _image_part(photo_file),
            ]},
        ],
        json_mode=True,
    )
    try:
        proposed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"unparseable bed outline: {raw[:200]}") from exc
    boundary = proposed.get("boundary")
    if (
        not isinstance(boundary, list)
        or not 4 <= len(boundary) <= 16
        or not all(
            isinstance(point, list)
            and len(point) == 2
            and all(isinstance(value, int | float) for value in point)
            for point in boundary
        )
    ):
        raise AIError("The suggested bed outline was incomplete.")
    if not all(0 <= point[0] <= width and 0 <= point[1] <= height for point in boundary):
        raise AIError("The suggested bed outline fell outside the selected region.")
    name = proposed.get("suggested_name", "")
    confidence = proposed.get("confidence", "low")
    return {
        "boundary": boundary,
        "suggested_name": name.strip()[:100] if isinstance(name, str) else "",
        "confidence": confidence if confidence in ("low", "medium", "high") else "low",
    }


# Plant fields AI enrichment may propose (empty-only; see enrich()).
ENRICHABLE_FIELDS = [
    "botanical_name", "sun", "water_needs", "mature_height", "mature_width",
    "toxicity_notes", "soil_notes", "foliage", "spring_care", "summer_care",
    "fall_care", "winter_care", "pruning_recommendations", "problems_to_watch",
]
CHOICE_FIELDS = {
    "sun": ["full", "part", "shade"],
    "water_needs": ["low", "moderate", "high"],
    "foliage": ["evergreen", "deciduous", "semi"],
}


def enrich(plant, region: str) -> dict:
    """Propose values for the plant's EMPTY enrichable fields only."""
    empty = [f for f in ENRICHABLE_FIELDS if not getattr(plant, f)]
    if not empty:
        return {}
    constraints = {f: CHOICE_FIELDS[f] for f in empty if f in CHOICE_FIELDS}
    system = (
        "You fill in missing horticultural reference data for a home gardener in "
        f"{region or 'the Pacific Northwest, USA'}. Respond ONLY with a JSON object "
        f"containing at most these keys: {empty}. Omit any field you are not "
        f"reasonably sure about. Constrained fields must use exactly one of the "
        f"allowed values: {json.dumps(constraints)}. Free-text fields: short, "
        "practical, no marketing prose. Sizes like '6-8 ft' are preferred over "
        "false precision. Seasonal care should be specific to this plant and region. "
        "For pruning_recommendations, say when and how to prune and include important "
        "times or situations when pruning should be avoided. For problems_to_watch, "
        "include only the most likely pests, diseases, and environmental stresses; "
        "give early signs and a brief low-risk response rather than an exhaustive list."
    )
    desc = f"{plant.common_name}"
    if plant.cultivar:
        desc += f" '{plant.cultivar}'"
    if plant.botanical_name:
        desc += f" ({plant.botanical_name})"
    known = {
        field: getattr(plant, field)
        for field in ("sun", "water_needs", "soil_notes", "foliage")
        if getattr(plant, field)
    }
    if known:
        desc += f". Known growing details: {json.dumps(known)}"
    raw, sources = complete(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"The plant: {desc}"}],
        json_mode=True, web=True,
    )
    try:
        proposed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"unparseable enrichment: {raw[:200]}") from exc
    # hard filter: empty-only, known fields, valid choices
    clean = {}
    for field, value in proposed.items():
        if field not in empty or not isinstance(value, str) or not value.strip():
            continue
        if field in CHOICE_FIELDS and value not in CHOICE_FIELDS[field]:
            continue
        clean[field] = value.strip()
    if clean and sources:
        clean["_sources"] = sources
    return clean


def ask(question: str, context: str, region: str) -> tuple[str, list[dict]]:
    system = (
        "You are the garden notebook's assistant for a home gardener in "
        f"{region or 'the Pacific Northwest, USA'}. Answer from the provided garden "
        "records where possible; say so when you're generalizing instead. Practical, "
        "warm, concise. Today's records follow as JSON."
    )
    return complete([
        {"role": "system", "content": system},
        {"role": "user", "content": f"My garden records:\n{context}\n\nQuestion: {question}"},
    ], web=True)


def lookup_plant(name: str, region: str) -> list[dict]:
    """Plant-creation lookup: candidate species/cultivars for a typed name,
    each with the profile fields the Add Plant form can pre-fill. Candidates
    are suggestions - the user picks one (or none) and everything remains
    editable before saving."""
    system = (
        "A home gardener is adding a plant to their garden notebook and typed a name. "
        f"They garden in {region or 'the Pacific Northwest, USA'}. Respond ONLY with a "
        'JSON object {"candidates": [...]} of 1-4 likely matches, most likely first. '
        "Each candidate: common_name, botanical_name, summary (1 sentence, what it is "
        "and why someone grows it), plant_type (one of: Annual/Biennial/Perennial/"
        "Bulb/Corm/Tuber/Shrub/Tree/Vine/Herb/Vegetable/Fruit/Groundcover), is_edible "
        "(bool), sun (full/part/shade), water_needs (low/moderate/high), foliage "
        "(evergreen/deciduous/semi or empty), mature_height, mature_width (like "
        "'6-8 ft'), soil_notes (short), toxicity_notes (pet/child safety - empty "
        "string if none known). Omit any field you are unsure of. If the name is "
        "ambiguous (e.g. 'daisy'), make the candidates meaningfully different."
    )
    raw, _sources = complete(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"The plant name they typed: {name}"}],
        json_mode=True, web=True,
    )
    try:
        candidates = json.loads(raw).get("candidates", [])
    except json.JSONDecodeError as exc:
        raise AIError(f"unparseable lookup: {raw[:200]}") from exc
    clean = []
    for c in candidates[:4]:
        if not isinstance(c, dict) or not c.get("common_name"):
            continue
        for f in ("sun", "water_needs", "foliage"):
            allowed = {"sun": ["full", "part", "shade"],
                       "water_needs": ["low", "moderate", "high"],
                       "foliage": ["evergreen", "deciduous", "semi"]}[f]
            if c.get(f) not in allowed:
                c.pop(f, None)
        clean.append(c)
    return clean
