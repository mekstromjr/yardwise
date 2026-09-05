"""Non-model tenancy helpers.

``garden_for(request)`` resolves which garden this request is tending: the
session-selected garden when the user has access to it (sharing, #27),
otherwise their own (lazily created on first visit).
"""

from .models import Garden

SESSION_KEY = "active_garden_id"


def garden_for(request) -> Garden:
    chosen = request.session.get(SESSION_KEY)
    if chosen:
        garden = Garden.objects.filter(pk=chosen).first()
        if garden and garden.accessible_to(request.user):
            return garden
        request.session.pop(SESSION_KEY, None)  # stale/revoked selection
    return Garden.for_user(request.user)
