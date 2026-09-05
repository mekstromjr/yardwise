"""Template context: unread notification count for the nav badge.

The integrator registers this in settings.py TEMPLATES context_processors as
``garden.context_processors.notifications``. A cheap COUNT only - no refresh
here; materialization happens on the center visit (garden.notify.refresh).
"""

from .models import Garden, Notification


def notifications(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    garden = Garden.for_user(request.user)
    return {"unread_count": Notification.visible_unread(garden=garden).count()}
