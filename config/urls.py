from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.http import HttpResponse
from django.urls import include, path


def healthz(_request):
    return HttpResponse("ok")


def readyz(_request):
    # Dependency-free by design (single replica): failing readiness on a slow
    # database would remove the only endpoint and turn degraded into a 503.
    return HttpResponse("ready")


urlpatterns = [
    path("", include("garden.urls")),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
