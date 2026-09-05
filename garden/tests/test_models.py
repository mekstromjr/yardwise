import datetime

import pytest
from django.db import IntegrityError

from garden.models import (
    Activity,
    ActivityType,
    Bed,
    OccurrenceStatus,
    Photo,
    Plant,
    ScheduleKind,
    SeasonWindow,
    Task,
)

pytestmark = pytest.mark.django_db


# --- SeasonWindow -----------------------------------------------------------


def test_window_resolves_within_year():
    w = SeasonWindow.objects.get(label="Late winter")
    start, end = w.resolve_for_year(2026)
    assert (start, end) == (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28))


def test_window_crossing_year_boundary():
    w = SeasonWindow.objects.get(label="Winter")
    start, end = w.resolve_for_year(2026)
    assert start == datetime.date(2026, 12, 1)
    assert end == datetime.date(2027, 2, 28)
    assert w.crosses_year_boundary


# --- Bed --------------------------------------------------------------------


def test_bed_codes_are_sequential_and_immutable_across_rename():
    b1 = Bed.objects.create(name="Front Entry Bed")
    b2 = Bed.objects.create(name="Blueberry Bed")
    assert (b1.code, b2.code) == ("BED-001", "BED-002")
    b1.name = "Front Door Bed"
    b1.save()
    b1.refresh_from_db()
    assert b1.code == "BED-001"


def test_active_bed_names_unique_but_archived_frees_the_name():
    # Names are unique per garden; a user's presence gives both rows the same
    # garden (tests/conftest.py stamps it, mirroring the backfill rule).
    from django.contrib.auth.models import User

    User.objects.create_user("michele", password="x")
    Bed.objects.create(name="Herb Bed")
    with pytest.raises(IntegrityError):
        Bed.objects.create(name="Herb Bed")


def test_archived_bed_frees_name_for_reuse():
    import django.utils.timezone as tz

    b1 = Bed.objects.create(name="Herb Bed")
    b1.archived_at = tz.now()
    b1.save()
    b2 = Bed.objects.create(name="Herb Bed")  # allowed: old one archived
    assert b1.code != b2.code  # history remains unambiguous via codes


# --- Task lifecycle ---------------------------------------------------------


def make_task(**kwargs) -> Task:
    defaults = {"title": "Test task", "schedule_kind": ScheduleKind.EXACT_ONCE}
    defaults.update(kwargs)
    return Task.objects.create(**defaults)


def test_exact_once_completion_creates_no_next():
    t = make_task(due_on=datetime.date(2026, 3, 15))
    occ = t.create_initial_occurrence()
    nxt = occ.complete()
    assert nxt is None
    occ.refresh_from_db()
    assert occ.status == OccurrenceStatus.COMPLETED


def test_exact_yearly_advances_one_year_and_preserves_history():
    t = make_task(schedule_kind=ScheduleKind.EXACT_YEARLY, due_on=datetime.date(2026, 3, 15))
    occ = t.create_initial_occurrence()
    nxt = occ.complete(on=datetime.date(2026, 3, 20))
    assert nxt.due_on == datetime.date(2027, 3, 15)
    assert t.occurrences.count() == 2
    occ.refresh_from_db()
    assert occ.completed_on == datetime.date(2026, 3, 20)  # actual date preserved (AC-126)


def test_interval_after_completion_counts_from_completion_date():
    t = make_task(
        schedule_kind=ScheduleKind.INTERVAL, interval_count=6, interval_unit="weeks"
    )
    occ = t.create_initial_occurrence()
    nxt = occ.complete(on=datetime.date(2026, 5, 1))
    assert nxt.due_on == datetime.date(2026, 6, 12)  # 6 weeks after actual completion


def test_interval_months_clamps_month_end():
    t = make_task(
        schedule_kind=ScheduleKind.INTERVAL,
        interval_count=1,
        interval_unit="months",
        interval_anchor="fixed",
        due_on=datetime.date(2026, 1, 31),
    )
    occ = t.create_initial_occurrence()
    assert occ.due_on == datetime.date(2026, 2, 28)  # Jan 31 + 1 month


def test_window_yearly_completion_schedules_next_years_window():
    w = SeasonWindow.objects.get(label="Late winter")
    t = make_task(schedule_kind=ScheduleKind.WINDOW_YEARLY, window=w)
    occ = t.occurrences.create(
        window_start=datetime.date(2026, 2, 1), window_end=datetime.date(2026, 2, 28)
    )
    nxt = occ.complete(on=datetime.date(2026, 2, 10))
    assert nxt.window_start == datetime.date(2027, 2, 1)
    assert nxt.window_end == datetime.date(2027, 2, 28)


def test_skip_preserves_history_and_still_schedules_next():
    t = make_task(schedule_kind=ScheduleKind.EXACT_YEARLY, due_on=datetime.date(2026, 3, 15))
    occ = t.create_initial_occurrence()
    nxt = occ.skip()
    occ.refresh_from_db()
    assert occ.status == OccurrenceStatus.SKIPPED
    assert nxt.due_on.year == 2027


def test_archived_task_stops_recurring():
    import django.utils.timezone as tz

    t = make_task(schedule_kind=ScheduleKind.EXACT_YEARLY, due_on=datetime.date(2026, 3, 15))
    occ = t.create_initial_occurrence()
    t.archived_at = tz.now()
    t.save()
    assert occ.complete() is None


def test_window_occurrence_due_and_overdue_semantics():
    w = SeasonWindow.objects.get(label="Late winter")
    t = make_task(schedule_kind=ScheduleKind.WINDOW_YEARLY, window=w)
    occ = t.occurrences.create(
        window_start=datetime.date(2026, 2, 1), window_end=datetime.date(2026, 2, 28)
    )
    assert not occ.is_due_now(today=datetime.date(2026, 1, 15))  # before window
    assert occ.is_due_now(today=datetime.date(2026, 2, 10))  # inside window
    assert not occ.is_overdue(today=datetime.date(2026, 2, 10))  # window still open
    assert occ.is_overdue(today=datetime.date(2026, 3, 1))  # window closed


def test_initial_window_occurrence_rolls_to_next_year_when_window_passed():
    w = SeasonWindow.objects.get(label="Late winter")
    t = make_task(schedule_kind=ScheduleKind.WINDOW_YEARLY, window=w)
    occ = t.create_initial_occurrence()
    today = datetime.date.today()
    assert occ.window_end >= today  # never schedules an already-closed window


# --- Activity ---------------------------------------------------------------


def test_activity_requires_plant_or_bed():
    at = ActivityType.objects.get(name="Pruned")
    with pytest.raises(IntegrityError):
        Activity.objects.create(activity_type=at, performed_on=datetime.date.today())


def test_activity_bed_scoped_is_valid():
    at = ActivityType.objects.get(name="Mulched")
    bed = Bed.objects.create(name="Front Bed")
    a = Activity.objects.create(activity_type=at, bed=bed, performed_on=datetime.date.today())
    assert a.pk


# --- Photo ------------------------------------------------------------------


def test_photo_derives_season_and_year_but_respects_overrides():
    p = Photo(taken_on=datetime.date(2026, 7, 4))
    p.save()
    assert (p.season, p.year) == ("summer", 2026)
    p2 = Photo(taken_on=datetime.date(2026, 12, 15), season="fall")  # user says fall
    p2.save()
    assert p2.season == "fall"  # override respected


# --- Plant ------------------------------------------------------------------


def test_plant_saves_with_only_a_name():
    p = Plant.objects.create(common_name="Fuyu Persimmon")
    assert p.pk and not p.is_watched


def test_watch_is_a_reason_not_a_flag():
    p = Plant.objects.create(common_name="Blueberry", watch_reason="Newly planted")
    assert p.is_watched


# --- Photo derivatives & EXIF (#11) ------------------------------------------


def _upload(name="big.jpg", size=(2400, 1600), exif_date=None):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    img = Image.new("RGB", size, "green")
    buf = io.BytesIO()
    exif = None
    if exif_date:
        exif = img.getexif()
        exif[306] = exif_date  # DateTime
    img.save(buf, "JPEG", exif=exif.tobytes() if exif else b"")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), "image/jpeg")


def test_photo_generates_web_and_thumb_derivatives():
    from PIL import Image

    p = Photo(file=_upload())
    p.save()
    assert p.file_web and p.file_thumb
    with p.file_web.open("rb") as fh:
        assert max(Image.open(fh).size) <= 1600
    with p.file_thumb.open("rb") as fh:
        assert max(Image.open(fh).size) <= 400
    assert p.web_url and p.thumb_url


def test_photo_reads_exif_date_and_derives_season():
    p = Photo(file=_upload(exif_date="2025:07:04 10:00:00"))
    p.save()
    assert str(p.taken_on) == "2025-07-04"
    assert (p.season, p.year) == ("summer", 2025)


def test_photo_without_exif_keeps_null_date():
    p = Photo(file=_upload())
    p.save()
    assert p.taken_on is None
    assert p.web_url  # fallback chain still yields a url


def test_large_jpeg_derivatives_bounded_and_correct():
    """The reduced-scale decode path (Image.draft) must still yield correct,
    orientation-preserved derivatives from a big JPEG."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from garden.models.photos import THUMB_MAX, WEB_MAX

    buf = io.BytesIO()
    Image.new("RGB", (4000, 3000), "green").save(buf, "JPEG", quality=85)
    p = Photo(file=SimpleUploadedFile("big.jpg", buf.getvalue(), "image/jpeg"))
    p.save()
    p.file_web.open("rb"); web = Image.open(p.file_web); web.load()
    p.file_thumb.open("rb"); thumb = Image.open(p.file_thumb); thumb.load()
    assert max(web.size) <= WEB_MAX and max(web.size) > THUMB_MAX
    assert max(thumb.size) <= THUMB_MAX
    assert web.size[0] / web.size[1] == pytest.approx(4000 / 3000, rel=0.02)
