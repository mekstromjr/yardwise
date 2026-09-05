"""Shared test plumbing for per-user gardens.

Most tests predate tenancy and create rows straight through the ORM with no
garden set, then assert visibility through views - which now scope everything
by the request user's garden. Rather than editing every such test, this
autouse fixture mirrors the production backfill rule: a row saved without a
garden is stamped with the earliest-created user's garden. Rows whose garden
is set explicitly (every view-created row, and every row in the tenancy
tests) are untouched, and tests with no users at all keep garden=None rows.
"""

import pytest
from django.db.models.signals import pre_save

from garden.models import (
    Activity,
    AISuggestion,
    Bed,
    ClimateProfile,
    Garden,
    HarvestEvent,
    IrrigationComponent,
    IrrigationEvent,
    IrrigationZone,
    JournalEntry,
    Notification,
    Photo,
    Plant,
    ProblemCase,
    ProblemType,
    SeasonalPlanting,
    Task,
    Variety,
)

GARDEN_SCOPED = (
    Activity, AISuggestion, Bed, ClimateProfile, HarvestEvent, IrrigationComponent,
    IrrigationEvent, IrrigationZone, JournalEntry, Notification, Photo, Plant,
    ProblemCase, ProblemType, SeasonalPlanting, Task, Variety,
)


@pytest.fixture(autouse=True)
def _stamp_default_garden(db):
    from django.contrib.auth.models import User

    def stamp(sender, instance, **kwargs):
        if instance.garden_id is None:
            user = User.objects.order_by("id").first()
            if user is not None:
                instance.garden_id = Garden.for_user(user).pk

    for model in GARDEN_SCOPED:
        pre_save.connect(stamp, sender=model, weak=False)
    yield
    for model in GARDEN_SCOPED:
        pre_save.disconnect(stamp, sender=model)
