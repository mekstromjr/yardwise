"""Non-model tenancy helpers.

``garden_for(request)`` is the one call every view makes to resolve the
request user's garden (get_or_create - a first visit lazily creates it).
"""

from .models import Garden


def garden_for(request) -> Garden:
    return Garden.for_user(request.user)
