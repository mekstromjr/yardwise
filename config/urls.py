from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


@login_required
def serve_media(request, path):
    # MEDIA_ROOT read per-request (not captured at import) so test overrides
    # and env changes behave; login gate keeps photos non-public (PDD 11).
    return serve(request, path, document_root=settings.MEDIA_ROOT)


def healthz(_request):
    return HttpResponse("ok")


def readyz(_request):
    # Dependency-free by design (single replica): failing readiness on a slow
    # database would remove the only endpoint and turn degraded into a 503.
    return HttpResponse("ready")


urlpatterns = [
    path("", include("garden.urls")),
    # Uploaded photos/imagery. Whitenoise only serves collected STATIC files;
    # media needs its own route in every environment - and gating it behind
    # login satisfies the PDD's photos-not-publicly-accessible requirement.
    # django.views.static.serve is fine at family scale (single household).
    re_path(r"^media/(?P<path>.*)$", serve_media, name="media"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
]


