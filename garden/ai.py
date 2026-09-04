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


class AIError(Exception):
    """Raised for transport/parse failures; views translate to a calm message."""


def complete(messages: list[dict], json_mode: bool = False) -> str:
    payload = {"model": model(), "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
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
        return body["choices"][0]["message"]["content"]
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
    raw = complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
        json_mode=True,
    )
    try:
        out = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"unparseable identification: {raw[:200]}") from exc
    out.setdefault("kind", "unsure")
    out.setdefault("confidence", "low")
    return out


# Plant fields AI enrichment may propose (empty-only; see enrich()).
ENRICHABLE_FIELDS = [
    "botanical_name", "sun", "water_needs", "mature_height", "mature_width",
    "toxicity_notes", "soil_notes", "foliage",
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
        "false precision."
    )
    desc = f"{plant.common_name}"
    if plant.cultivar:
        desc += f" '{plant.cultivar}'"
    if plant.botanical_name:
        desc += f" ({plant.botanical_name})"
    raw = complete(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"The plant: {desc}"}],
        json_mode=True,
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
    return clean


def ask(question: str, context: str, region: str) -> str:
    system = (
        "You are the garden notebook's assistant for a home gardener in "
        f"{region or 'the Pacific Northwest, USA'}. Answer from the provided garden "
        "records where possible; say so when you're generalizing instead. Practical, "
        "warm, concise. Today's records follow as JSON."
    )
    return complete([
        {"role": "system", "content": system},
        {"role": "user", "content": f"My garden records:\n{context}\n\nQuestion: {question}"},
    ])


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
    raw = complete(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"The plant name they typed: {name}"}],
        json_mode=True,
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
