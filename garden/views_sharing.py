"""Garden sharing (#27): invite by username, switch active garden, revoke.

Owner-only management; membership grants full tending access. The switcher
writes one session key - every view resolves through garden_for(), so the
whole app follows without further changes.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import Garden
from .tenancy import SESSION_KEY


@require_POST
@login_required
def switch_garden(request):
    garden = Garden.objects.filter(pk=request.POST.get("garden")).first()
    if garden and garden.accessible_to(request.user):
        request.session[SESSION_KEY] = garden.pk
    return redirect(request.POST.get("next") or "today")


@require_POST
@login_required
def invite_member(request):
    own = Garden.for_user(request.user)
    username = (request.POST.get("username") or "").strip()
    user = get_user_model().objects.filter(username__iexact=username).first()
    if user is None:
        messages.error(request, f'No account named "{username}" - they need to sign in once first.')
    elif user == request.user:
        messages.error(request, "That's you - you're already the owner.")
    else:
        own.members.add(user)
        messages.success(request, f"{user.username} can now tend your garden.")
    return redirect("me")


@require_POST
@login_required
def remove_member(request, user_id):
    own = Garden.for_user(request.user)
    own.members.remove(user_id)
    return redirect("me")
