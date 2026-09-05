"""AI assistance views (PDD section 9). Every path here ends in an explicit
user decision; AI never writes garden records itself."""

import datetime
import json

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from . import ai
from .models import (
    AISuggestion,
    Photo,
    Plant,
    SuggestionKind,
    SuggestionStatus,
)


def _require_ai():
    if not ai.enabled():
        raise Http404


def _garden_context() -> str:
    """Compact JSON snapshot the model can reason over."""
    from .models import CaseStatus, OccurrenceStatus, ProblemCase, TaskOccurrence

    today = datetime.date.today()
    plants = list(
        Plant.objects.filter(status="active").values_list("common_name", "cultivar")[:200]
    )
    problems = list(
        ProblemCase.objects.exclude(status=CaseStatus.RESOLVED)
        .values_list("problem_type__name", "status")[:50]
    )
    tasks = [
        {"title": o.task.title, "when": str(o.effective_due)}
        for o in TaskOccurrence.objects.filter(status=OccurrenceStatus.PENDING)
        .select_related("task")[:50]
    ]
    return json.dumps({
        "date": str(today),
        "plants": [f"{n} '{c}'" if c else n for n, c in plants],
        "open_problems": [f"{n} ({s})" for n, s in problems],
        "pending_tasks": tasks,
    })


@login_required
def identify(request):
    _require_ai()
    if request.method == "POST" and request.FILES.get("photo"):
        photo = Photo.objects.create(file=request.FILES["photo"], uploaded_by=request.user)
        question = request.POST.get("question") or "What is this?"
        try:
            result = ai.identify(photo.file, question, region="", context=_garden_context())
        except ai.AIError:
            msg = "The assistant couldn't be reached - try again in a minute."
            return render(request, "garden/ai/identify.html",
                          {"nav": "plants", "error": msg})
        suggestion = AISuggestion.objects.create(
            kind=SuggestionKind.IDENTIFY, question=question, response=result,
            photo=photo, created_by=request.user,
        )
        return redirect("ai-suggestion", pk=suggestion.pk)
    return render(request, "garden/ai/identify.html", {"nav": "plants"})


@login_required
def suggestion_detail(request, pk):
    suggestion = get_object_or_404(AISuggestion, pk=pk, kind=SuggestionKind.IDENTIFY)
    result = suggestion.response
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "problem" and result.get("kind") in ("weed", "pest", "disease"):
            from .models import ProblemCase, ProblemType

            ptype, _ = ProblemType.objects.get_or_create(
                kind=result["kind"], name__iexact=result.get("name", "Unknown"),
                archived_at__isnull=True,
                defaults={"kind": result["kind"], "name": result.get("name", "Unknown"),
                          "scientific_name": result.get("scientific_name", ""),
                          "control_notes": result.get("action_advice", "")},
            )
            case = ProblemCase.objects.create(
                problem_type=ptype, first_observed=datetime.date.today(),
                notes=result.get("summary", ""), created_by=request.user,
            )
            if suggestion.photo:
                case.photos.add(suggestion.photo)
            suggestion.status = SuggestionStatus.ACCEPTED
            suggestion.save(update_fields=["status"])
            return redirect("problem-detail", pk=case.pk)
        if action == "plant":
            plant = Plant.objects.create(
                common_name=result.get("name", "Unknown plant"),
                botanical_name=result.get("scientific_name", ""),
                notes=result.get("summary", ""), created_by=request.user,
            )
            if suggestion.photo:
                plant.photos.add(suggestion.photo)
                plant.primary_photo = suggestion.photo
                plant.save(update_fields=["primary_photo"])
            suggestion.status = SuggestionStatus.ACCEPTED
            suggestion.save(update_fields=["status"])
            return redirect("plant-detail", pk=plant.pk)
        if action in ("saved", "dismissed"):
            suggestion.status = action
            suggestion.save(update_fields=["status"])
            return redirect("plant-list")
    return render(request, "garden/ai/suggestion.html", {
        "nav": "plants", "s": suggestion, "r": result,
        "low_confidence": result.get("confidence") == "low",
    })


@login_required
def plant_enrich(request, pk):
    _require_ai()
    plant = get_object_or_404(Plant, pk=pk)
    if request.method == "POST" and request.POST.get("apply"):
        suggestion = get_object_or_404(
            AISuggestion, pk=request.POST["suggestion"], plant=plant,
            status=SuggestionStatus.PENDING,
        )
        chosen = [f for f in suggestion.response if request.POST.get(f"accept_{f}")]
        for field in chosen:
            if not getattr(plant, field):  # empty-only, re-checked at apply time
                setattr(plant, field, suggestion.response[field])
        plant.save()
        suggestion.status = SuggestionStatus.ACCEPTED if chosen else SuggestionStatus.DISMISSED
        suggestion.accepted_fields = chosen
        suggestion.save(update_fields=["status", "accepted_fields"])
        return redirect("plant-detail", pk=plant.pk)
    if request.method == "POST":
        try:
            proposed = ai.enrich(plant, region="")
        except ai.AIError:
            proposed = None
        if not proposed:
            return render(request, "garden/ai/enrich.html", {
                "nav": "plants", "plant": plant,
                "error": "Nothing to suggest - the record may already be complete, "
                         "or the assistant couldn't be reached.",
            })
        suggestion = AISuggestion.objects.create(
            kind=SuggestionKind.ENRICH, response=proposed, plant=plant,
            created_by=request.user,
        )
        sources = proposed.pop("_sources", []) if isinstance(proposed, dict) else []
        fields = [(f, Plant._meta.get_field(f).verbose_name, v) for f, v in proposed.items()]
        return render(request, "garden/ai/enrich.html", {
            "nav": "plants", "plant": plant, "suggestion": suggestion, "fields": fields,
            "sources": sources,
        })
    return render(request, "garden/ai/enrich.html", {"nav": "plants", "plant": plant})


@login_required
def assistant(request):
    """The assistant's home: ask (with sources), identify entry, question
    history, and saved-for-later identifications - all one screen."""
    _require_ai()
    answer, question, sources = None, "", []
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        if question:
            try:
                answer, sources = ai.ask(question, _garden_context(), region="")
            except ai.AIError:
                answer = "The assistant couldn't be reached - try again in a minute."
            AISuggestion.objects.create(
                kind=SuggestionKind.QUESTION, question=question,
                response={"answer": answer, "sources": sources},
                created_by=request.user, status=SuggestionStatus.ACCEPTED,
            )
    history = AISuggestion.objects.filter(kind=SuggestionKind.QUESTION)[:10]
    saved = AISuggestion.objects.filter(
        kind=SuggestionKind.IDENTIFY, status=SuggestionStatus.SAVED
    )[:10]
    return render(request, "garden/ai/assistant.html", {
        "nav": "assistant", "question": question, "answer": answer,
        "sources": sources, "history": history, "saved": saved,
    })


# Fields a lookup candidate may pre-fill on the Add Plant form.
LOOKUP_PREFILL_FIELDS = [
    "common_name", "botanical_name", "is_edible", "sun", "water_needs",
    "foliage", "mature_height", "mature_width", "soil_notes", "toxicity_notes",
]


@login_required
def plant_lookup(request):
    """Name -> AI candidates -> pick one -> Add Plant form arrives pre-filled.

    Nothing is saved here: the chosen candidate goes into the session and the
    regular Add Plant form (fully editable) does the actual creation."""
    _require_ai()
    name = (request.POST.get("name") or request.GET.get("name") or "").strip()
    if request.method == "POST" and request.POST.get("choose"):
        candidates = request.session.get("plant_lookup_candidates") or []
        idx = int(request.POST["choose"])
        if 0 <= idx < len(candidates):
            chosen = candidates[idx]
            prefill = {f: chosen[f] for f in LOOKUP_PREFILL_FIELDS if f in chosen}
            ptype = chosen.get("plant_type", "")
            if ptype:  # match user vocabulary case-insensitively; never create vocab
                from .models import PlantType

                match = PlantType.objects.filter(
                    name__iexact=ptype, archived_at__isnull=True
                ).first()
                if match:
                    prefill["plant_type"] = match.pk
            request.session["plant_prefill"] = prefill
            request.session["plant_prefill_note"] = chosen.get("summary", "")
        return redirect("plant-add")
    if request.method == "POST" and name:
        try:
            candidates = ai.lookup_plant(name, region="")
        except ai.AIError:
            candidates = []
        if not candidates:
            return render(request, "garden/ai/lookup.html", {
                "nav": "plants", "name": name,
                "error": "Couldn't look that up right now - you can still add it by hand.",
            })
        request.session["plant_lookup_candidates"] = candidates
        return render(request, "garden/ai/lookup.html",
                      {"nav": "plants", "name": name, "candidates": candidates})
    return render(request, "garden/ai/lookup.html", {"nav": "plants", "name": name})
