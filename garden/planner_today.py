"""Today-screen feed for planner milestones (#24, PDD 6.6/6.8 lite).

views.py stays untouched: the integrator calls due_milestones() and renders
the items alongside task occurrences. No rows are stored - milestones are
recomputed from the variety offsets and climate profile every time, so a
climate edit reflows Today automatically.
"""

import datetime
from typing import NamedTuple

from .models import ClimateProfile, PlantingStatus, SeasonalPlanting


class MilestoneItem(NamedTuple):
    label: str
    date: datetime.date
    planting: SeasonalPlanting


def due_milestones(on: datetime.date | None = None, horizon_days: int = 14) -> list[MilestoneItem]:
    """Milestones due now or within `horizon_days`, oldest first.

    Recently-passed milestones (within the horizon looking back) stay visible
    rather than silently vanishing - a missed sowing window is exactly what
    the gardener wants to hear about.
    """
    on = on or datetime.date.today()
    window_start = on - datetime.timedelta(days=horizon_days)
    window_end = on + datetime.timedelta(days=horizon_days)
    climate = ClimateProfile.load()

    plantings = (
        SeasonalPlanting.objects.filter(
            year__in=(on.year, on.year + 1), archived_at__isnull=True
        )
        .exclude(status=PlantingStatus.FINISHED)
        .select_related("variety", "bed")
    )
    items = [
        MilestoneItem(label, date, planting)
        for planting in plantings
        for label, date in planting.compute_milestones(climate)
        if window_start <= date <= window_end
    ]
    items.sort(key=lambda item: item.date)
    return items
