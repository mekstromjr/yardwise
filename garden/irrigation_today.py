"""Helpers for surfacing irrigation on existing screens (bed detail, Today).

Existing views are not edited by the irrigation module; the integrator calls
these from wherever bed/today context is built.
"""

from .models import ComponentCondition, IrrigationComponent, IrrigationZone, ZoneStatus

# Conditions that mean a component actively needs attention.
_FAULT_CONDITIONS = [
    ComponentCondition.NEEDS_ADJUSTMENT,
    ComponentCondition.LEAKING,
    ComponentCondition.CLOGGED,
    ComponentCondition.BROKEN,
]


def zones_for_bed(bed):
    """Active irrigation zones known to serve this bed (may be empty -
    'no known coverage' is meaningful information, not an error)."""
    return bed.irrigation_zones.filter(archived_at__isnull=True)


def needs_repair_count(garden=None):
    """How many irrigation things need attention: zones flagged needs_repair
    plus unarchived components in a fault condition (scoped to one garden)."""
    zones = IrrigationZone.objects.filter(
        garden=garden, archived_at__isnull=True, status=ZoneStatus.NEEDS_REPAIR
    ).count()
    components = IrrigationComponent.objects.filter(
        garden=garden, archived_at__isnull=True, condition__in=_FAULT_CONDITIONS
    ).count()
    return zones + components
