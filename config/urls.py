from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.http import HttpResponse
from django.urls import include, path, re_path


@login_required
def serve_media(request, path):
    # Streams through the default storage backend (Garage S3 in prod,
    # filesystem in dev/tests), so image URLs stay on this host and the
    # login + garden-membership gate applies regardless of where bytes
    # live (#27/#28). Legacy files with no owning record are login-only.
    import mimetypes

    from django.core.files.storage import default_storage
    from django.http import FileResponse, Http404

    from garden.models import MapLayer, Photo
    from garden.tenancy import garden_for

    record = (
        Photo.objects.filter(file=path).first()
        or MapLayer.objects.filter(image=path).first()
    )
    if record is not None and record.garden_id is not None:
        garden = garden_for(request)
        owns = record.garden_id == garden.pk
        if not owns and not record.garden.accessible_to(request.user):
            raise Http404
    if not default_storage.exists(path):
        raise Http404
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(default_storage.open(path, "rb"), content_type=content_type)


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


