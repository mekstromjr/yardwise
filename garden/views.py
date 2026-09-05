import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PlantForm
from .models import (
    Bed,
    OccurrenceStatus,
    Photo,
    Plant,
    PlantLocation,
    PlantStatus,
    PlantType,
    Tag,
    TaskOccurrence,
)
from .tenancy import garden_for

COMING_SOON_DAYS = 14  # "this week & next" horizon for the Today screen


def _describe_when(occ: TaskOccurrence) -> str:
    if occ.due_on:
        return occ.due_on.strftime("%b %-d")
    return f"{occ.window_start:%b %-d} - {occ.window_end:%b %-d}"


def _season_label(d: datetime.date) -> str:
    part = ["Early", "Mid", "Late"][min((d.day - 1) // 10, 2)]
    season = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
              6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall", 11: "fall"}[d.month]
    return f"{part} {season}"


@login_required
def today(request):
    g = garden_for(request)
    today_ = datetime.date.today()
    horizon = today_ + datetime.timedelta(days=COMING_SOON_DAYS)
    pending = TaskOccurrence.objects.filter(
        status=OccurrenceStatus.PENDING, task__archived_at__isnull=True, task__garden=g
    ).select_related("task")

    overdue, due_now, coming_soon = [], [], []
    for occ in pending:
        occ.describe_when = _describe_when(occ)
        if occ.is_overdue(today_):
            overdue.append(occ)
        elif occ.is_due_now(today_):
            due_now.append(occ)
        elif (occ.due_on or occ.window_start) <= horizon:
            coming_soon.append(occ)

    from .models import CaseStatus, ProblemCase

    followups = list(
        ProblemCase.objects.filter(garden=g)
        .exclude(status=CaseStatus.RESOLVED)
        .filter(follow_up_on__isnull=False, follow_up_on__lte=horizon)
        .select_related("problem_type", "bed")
        .order_by("follow_up_on")
    )
    open_problem_count = (
        ProblemCase.objects.filter(garden=g).exclude(status=CaseStatus.RESOLVED).count()
    )

    from .irrigation_today import needs_repair_count
    from .planner_today import due_milestones

    planner_milestones = due_milestones(on=today_, horizon_days=COMING_SOON_DAYS, garden=g)
    repair_count = needs_repair_count(garden=g)

    hour = datetime.datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    return render(request, "garden/today.html", {
        "followups": followups,
        "open_problem_count": open_problem_count,
        "planner_milestones": planner_milestones,
        "repair_count": repair_count,
        "nav": "today",
        "today": today_,
        "season_label": _season_label(today_),
        "greeting": greeting,
        "has_any_plants": Plant.objects.filter(garden=g).exists(),
        "overdue": overdue,
        "due_now": due_now,
        "coming_soon": coming_soon,
        "watched": Plant.objects.filter(garden=g, status=PlantStatus.ACTIVE).exclude(
            watch_reason=""
        ),
    })


@login_required
def plant_list(request):
    g = garden_for(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", PlantStatus.ACTIVE)
    valid_statuses = {value for value, _label in PlantStatus.choices}
    if status != "all" and status not in valid_statuses:
        status = PlantStatus.ACTIVE

    plants = (
        Plant.objects.filter(garden=g)
        .select_related("primary_photo")
        .prefetch_related("locations__bed")
    )
    if status != "all":
        plants = plants.filter(status=status)
    if q:
        plants = plants.filter(
            Q(common_name__icontains=q)
            | Q(botanical_name__icontains=q)
            | Q(cultivar__icontains=q)
            | Q(tags__name__icontains=q)
            | Q(locations__bed__name__icontains=q)
        ).distinct()

    bed = request.GET.get("bed", "")
    plant_type = request.GET.get("plant_type", "")
    use = request.GET.get("use", "")
    tag = request.GET.get("tag", "")
    bed = bed if bed.isdigit() else ""
    plant_type = plant_type if plant_type.isdigit() else ""
    tag = tag if tag.isdigit() else ""
    if bed:
        plants = plants.filter(locations__is_current=True, locations__bed_id=bed)
    if plant_type:
        plants = plants.filter(plant_type_id=plant_type)
    if use == "edible":
        plants = plants.filter(is_edible=True)
    elif use == "ornamental":
        plants = plants.filter(is_ornamental=True)
    else:
        use = ""
    if tag:
        plants = plants.filter(tags__id=tag)
    plants = plants.distinct()

    return render(request, "garden/plants/list.html", {
        "nav": "plants",
        "plants": plants,
        "q": q,
        "result_count": plants.count(),
        "beds": Bed.objects.filter(garden=g, archived_at__isnull=True),
        "plant_types": PlantType.objects.filter(archived_at__isnull=True),
        "tags": Tag.objects.filter(archived_at__isnull=True),
        "statuses": [("all", "All statuses"), *PlantStatus.choices],
        "selected_bed": bed,
        "selected_plant_type": plant_type,
        "selected_use": use,
        "selected_tag": tag,
        "selected_status": status,
        "advanced_filters_active": any(
            (bed, plant_type, use, tag, status != PlantStatus.ACTIVE)
        ),
        "filters_active": any((q, bed, plant_type, use, tag, status != PlantStatus.ACTIVE)),
    })


@login_required
def plant_detail(request, pk):
    plant = get_object_or_404(Plant, pk=pk, garden=garden_for(request))
    harvests = list(plant.harvests.select_related("unit")[:50])
    timeline = [
        {"label": str(a.activity_type), "note": a.note, "on": a.performed_on}
        for a in plant.activities.select_related("activity_type")[:50]
    ] + [
        {"label": "Harvest", "note": _harvest_line(h), "on": h.harvested_on}
        for h in harvests
    ]
    timeline.sort(key=lambda item: item["on"], reverse=True)

    year = datetime.date.today().year
    totals = {}
    for h in harvests:
        if h.harvested_on.year == year and h.quantity and h.unit:
            totals[h.unit.name] = totals.get(h.unit.name, 0) + h.quantity
    season_total = ", ".join(f"{float(q):g} {u}" for u, q in totals.items())

    active_problems = plant.problem_cases.exclude(status="resolved").select_related(
        "problem_type"
    )

    return render(request, "garden/plants/detail.html", {
        "nav": "plants",
        "plant": plant,
        "active_problems": active_problems,
        "timeline": timeline,
        "photos": plant.photos.all()[:24],
        "journal_entries": plant.journal_entries.all()[:10],
        "season_total": season_total,
        "year": year,
    })


@login_required
@require_POST
def plant_archive(request, pk):
    plant = get_object_or_404(Plant, pk=pk, garden=garden_for(request))
    plant.status = PlantStatus.ARCHIVED
    plant.archived_at = timezone.now()
    plant.save(update_fields=["status", "archived_at", "updated_at"])
    return redirect("plant-list")


@login_required
@require_POST
def plant_unarchive(request, pk):
    plant = get_object_or_404(
        Plant, pk=pk, garden=garden_for(request), status=PlantStatus.ARCHIVED
    )
    plant.status = PlantStatus.ACTIVE
    plant.archived_at = None
    plant.save(update_fields=["status", "archived_at", "updated_at"])
    return redirect("plant-detail", pk=plant.pk)


@login_required
@require_POST
def plant_delete(request, pk):
    plant = get_object_or_404(Plant, pk=pk, garden=garden_for(request))
    plant.delete()
    return redirect("plant-list")


def _harvest_line(h) -> str:
    parts = []
    if h.quantity and h.unit:
        parts.append(f"{float(h.quantity):g} {h.unit.name}")
    if h.quality:
        parts.append(h.quality)
    if h.notes:
        parts.append(h.notes)
    return " - ".join(parts)


@login_required
def plant_form(request, pk=None):
    g = garden_for(request)
    plant = get_object_or_404(Plant, pk=pk, garden=g) if pk else None
    # AI lookup hand-off: a chosen candidate pre-fills the ADD form (one-shot).
    prefill = request.session.pop("plant_prefill", None) if not plant else None
    prefill_note = request.session.pop("plant_prefill_note", "") if prefill else ""
    form = PlantForm(
        request.POST or None, request.FILES or None, instance=plant, initial=prefill, garden=g
    )
    if request.method == "POST" and form.is_valid():
        plant = form.save(commit=False)
        if not plant.created_by_id:
            plant.created_by = request.user
        plant.garden = g
        plant.save()
        form.save_m2m()
        _apply_photo_and_location(plant, form, request)
        return redirect("plant-detail", pk=plant.pk)
    if plant:  # pre-fill the location fields from the current placement
        loc = plant.current_locations.first()
        if loc:
            form.fields["bed"].initial = loc.bed_id
            form.fields["location_note"].initial = loc.location_note
    return render(request, "garden/plants/form.html", {
        "nav": "plants", "form": form, "prefill_note": prefill_note,
    })


def _apply_photo_and_location(plant: Plant, form: PlantForm, request):
    upload = form.cleaned_data.get("photo")
    if upload:
        photo = Photo.objects.create(
            file=upload, uploaded_by=request.user, garden=plant.garden
        )
        plant.photos.add(photo)
        if not plant.primary_photo:
            plant.primary_photo = photo
            plant.save(update_fields=["primary_photo"])

    bed = form.cleaned_data.get("bed")
    note = form.cleaned_data.get("location_note", "")
    current = plant.current_locations.first()
    if current and current.bed_id == (bed.pk if bed else None):
        if current.location_note != note:  # same bed, refined note: edit in place
            current.location_note = note
            current.save(update_fields=["location_note"])
    elif bed or note or current:
        # Placement changed: close the old row, open a new current one -
        # this IS the location-history rule, not an optimization.
        today_ = datetime.date.today()
        if current:
            current.is_current = False
            current.ended_on = today_
            current.save(update_fields=["is_current", "ended_on"])
        PlantLocation.objects.create(
            plant=plant, bed=bed, location_note=note, started_on=today_
        )


@login_required
def task_list(request):
    view = request.GET.get("view", "due")
    today_ = datetime.date.today()
    base = TaskOccurrence.objects.filter(
        task__archived_at__isnull=True, task__garden=garden_for(request)
    ).select_related("task", "task__category")
    if view == "completed":
        occurrences = base.exclude(status=OccurrenceStatus.PENDING).order_by("-completed_on")[:100]
    else:
        pending = list(base.filter(status=OccurrenceStatus.PENDING))
        if view == "due":
            occurrences = [o for o in pending if o.is_overdue(today_) or o.is_due_now(today_)]
        elif view == "upcoming":
            occurrences = [
                o for o in pending if not (o.is_overdue(today_) or o.is_due_now(today_))
            ]
        else:  # all
            occurrences = pending
    for occ in occurrences:
        occ.describe_when = _describe_when(occ)
    return render(request, "garden/tasks/list.html", {
        "nav": "tasks", "view": view, "occurrences": occurrences, "today": today_,
    })


@login_required
def task_form(request, pk=None):
    from .forms import TaskForm
    from .models import Task

    g = garden_for(request)
    task = get_object_or_404(Task, pk=pk, garden=g) if pk else None
    form = TaskForm(request.POST or None, instance=task, garden=g)
    if request.method == "POST" and form.is_valid():
        is_new = task is None
        task = form.save(commit=False)
        if not task.created_by_id:
            task.created_by = request.user
        task.garden = g
        task.save()
        form.save_m2m()
        if is_new:
            task.create_initial_occurrence()
        return redirect("task-list")
    return render(request, "garden/tasks/form.html", {"nav": "tasks", "form": form})


@login_required
def occurrence_action(request, pk, action):
    """POST: complete or skip an occurrence. Returns the refreshed row (htmx)
    or redirects back (no-JS fallback)."""
    occ = get_object_or_404(
        TaskOccurrence, pk=pk, status=OccurrenceStatus.PENDING,
        task__garden=garden_for(request),
    )
    if request.method != "POST":
        return redirect("task-list")
    if action == "complete":
        occ.complete(note=request.POST.get("note", ""))
    else:
        occ.skip()
    if request.htmx:
        occ.describe_when = _describe_when(occ)
        return render(request, "garden/tasks/_row_done.html", {"occ": occ})
    return redirect(request.POST.get("next") or "task-list")


def _save_photos(files, user, plant=None, garden=None):
    """Create Photo rows for uploads and link them where they belong."""
    photos = []
    for f in files:
        photo = Photo.objects.create(
            file=f, uploaded_by=user, garden=garden or (plant.garden if plant else None)
        )
        if plant:
            plant.photos.add(photo)
            if not plant.primary_photo_id:
                plant.primary_photo = photo
                plant.save(update_fields=["primary_photo"])
        photos.append(photo)
    return photos


@login_required
def activity_add(request, pk):
    from .forms import ActivityForm

    plant = get_object_or_404(Plant, pk=pk, garden=garden_for(request))
    form = ActivityForm(request.POST or None, request.FILES or None,
                        initial={"performed_on": datetime.date.today()})
    if request.method == "POST" and form.is_valid():
        activity = form.save(commit=False)
        activity.plant = plant
        activity.garden = plant.garden
        activity.created_by = request.user
        activity.save()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, plant):
            activity.photos.add(photo)
        return redirect("plant-detail", pk=plant.pk)
    return render(request, "garden/plants/activity_form.html",
                  {"nav": "plants", "plant": plant, "form": form})


@login_required
def harvest_add(request, pk):
    from .forms import HarvestForm

    plant = get_object_or_404(Plant, pk=pk, garden=garden_for(request))
    form = HarvestForm(request.POST or None, request.FILES or None,
                       initial={"harvested_on": datetime.date.today()})
    if request.method == "POST" and form.is_valid():
        harvest = form.save(commit=False)
        harvest.plant = plant
        harvest.garden = plant.garden
        harvest.created_by = request.user
        harvest.save()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, plant):
            harvest.photos.add(photo)
        return redirect("plant-detail", pk=plant.pk)
    return render(request, "garden/plants/harvest_form.html",
                  {"nav": "plants", "plant": plant, "form": form})


@login_required
def photo_add(request, pk):
    from .forms import PhotoForm

    plant = get_object_or_404(Plant, pk=pk, garden=garden_for(request))
    form = PhotoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        photo = form.save(commit=False)
        photo.uploaded_by = request.user
        photo.garden = plant.garden
        photo.save()
        form.save_m2m()
        plant.photos.add(photo)
        if not plant.primary_photo_id:
            plant.primary_photo = photo
            plant.save(update_fields=["primary_photo"])
        return redirect("plant-detail", pk=plant.pk)
    return render(request, "garden/plants/photo_form.html",
                  {"nav": "plants", "plant": plant, "form": form})


@login_required
def journal_list(request):
    from .models import JournalEntry

    entries = (
        JournalEntry.objects.filter(garden=garden_for(request))
        .prefetch_related("photos", "plants", "tags")
        .select_related("created_by")
    )
    q = request.GET.get("q", "").strip()
    if q:
        entries = entries.filter(
            Q(text__icontains=q) | Q(plants__common_name__icontains=q)
            | Q(tags__name__icontains=q)
        ).distinct()
    return render(request, "garden/journal/list.html",
                  {"nav": "journal", "entries": entries[:100], "q": q})


@login_required
def journal_add(request):
    import django.utils.timezone as tz

    from .forms import JournalForm

    g = garden_for(request)
    form = JournalForm(request.POST or None, request.FILES or None, garden=g)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.occurred_at = tz.now()
        entry.created_by = request.user
        entry.garden = g
        entry.save()
        form.save_m2m()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, garden=g):
            entry.photos.add(photo)
        return redirect("journal-list")
    return render(request, "garden/journal/form.html", {"nav": "journal", "form": form})


@login_required
def me(request):
    import os

    from .models import Garden
    from .tenancy import garden_for

    own = Garden.for_user(request.user)
    return render(request, "garden/me.html", {
        "nav": "me",
        "app_version": os.environ.get("YARDWISE_VERSION", "dev"),
        "own_garden": own,
        "active_garden": garden_for(request),
        "gardens": Garden.gardens_for(request.user),
        "garden_members": own.members.all(),
    })


@login_required
def problem_list(request):
    from .models import CaseStatus, ProblemCase

    kind = request.GET.get("kind", "")
    show = request.GET.get("show", "open")
    cases = (
        ProblemCase.objects.filter(garden=garden_for(request))
        .select_related("problem_type", "bed")
        .prefetch_related("plants")
    )
    if kind:
        cases = cases.filter(problem_type__kind=kind)
    if show == "open":
        cases = cases.exclude(status=CaseStatus.RESOLVED)
    return render(request, "garden/problems/list.html", {
        "nav": "plants", "cases": cases[:100], "kind": kind, "show": show,
    })


@login_required
def problem_add(request):
    from .forms import ProblemCaseForm
    from .models import ProblemType

    g = garden_for(request)
    initial = {"first_observed": datetime.date.today()}
    plant_pk = request.GET.get("plant")
    form = ProblemCaseForm(request.POST or None, request.FILES or None, initial=initial,
                           garden=g)
    if request.method == "POST" and form.is_valid():
        ptype, _ = ProblemType.objects.get_or_create(
            kind=form.cleaned_data["kind"],
            name__iexact=form.cleaned_data["type_name"].strip(),
            archived_at__isnull=True,
            garden=g,
            defaults={"kind": form.cleaned_data["kind"],
                      "name": form.cleaned_data["type_name"].strip(),
                      "garden": g},
        )
        case = form.save(commit=False)
        case.problem_type = ptype
        case.created_by = request.user
        case.garden = g
        case.save()
        form.save_m2m()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, garden=g):
            case.photos.add(photo)
        return redirect("problem-detail", pk=case.pk)
    if plant_pk:
        form.fields["plants"].initial = [plant_pk]
    return render(request, "garden/problems/form.html", {"nav": "plants", "form": form})


@login_required
def problem_detail(request, pk):
    from .models import CaseStatus, ProblemCase

    case = get_object_or_404(
        ProblemCase.objects.select_related("problem_type", "bed"),
        pk=pk, garden=garden_for(request),
    )
    if request.method == "POST":  # status change buttons
        new_status = request.POST.get("status")
        if new_status in CaseStatus.values:
            case.status = new_status
            case.last_observed = datetime.date.today()
            case.save(update_fields=["status", "last_observed"])
        return redirect("problem-detail", pk=pk)
    return render(request, "garden/problems/detail.html", {
        "nav": "plants", "case": case, "statuses": CaseStatus.choices,
        "treatments": case.treatments.all(),
    })


@login_required
def treatment_add(request, pk):
    from .forms import TreatmentForm
    from .models import CaseStatus, ProblemCase

    g = garden_for(request)
    case = get_object_or_404(ProblemCase, pk=pk, garden=g)
    form = TreatmentForm(request.POST or None, request.FILES or None,
                         initial={"treated_on": datetime.date.today()})
    if request.method == "POST" and form.is_valid():
        treatment = form.save(commit=False)
        treatment.case = case
        treatment.created_by = request.user
        treatment.save()
        for photo in _save_photos(form.cleaned_data["photos_upload"], request.user, garden=g):
            treatment.photos.add(photo)
        if case.status in (CaseStatus.MONITORING, CaseStatus.ACTIVE):
            case.status = CaseStatus.TREATING
            case.save(update_fields=["status"])
        return redirect("problem-detail", pk=case.pk)
    return render(request, "garden/problems/treatment_form.html",
                  {"nav": "plants", "case": case, "form": form})
