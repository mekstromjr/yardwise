"""YardWise Django settings.

Everything server-specific comes from environment variables so the same image
runs in dev, CI, and the cluster (see .env.example for the full list).
"""

import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


# No hardcoded fallback key. Production sets DJANGO_SECRET_KEY (from Vault via
# ESO); if it goes missing there, sessions breaking loudly on every restart
# beats running on a known key silently. Unset locally, a generated key is
# persisted to a gitignored file so runserver's auto-reload doesn't log you
# out on every code change.
def _local_dev_key() -> str:
    keyfile = BASE_DIR / ".dev-secret-key"
    try:
        key = keyfile.read_text().strip()
    except FileNotFoundError:
        key = ""
    if not key:
        key = get_random_secret_key()
        keyfile.write_text(key)
    return key


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or _local_dev_key()
DEBUG = env_bool("DJANGO_DEBUG", False)
def env_list(name: str, default: str = "") -> list[str]:
    return [v for v in os.environ.get(name, default).split(",") if v]


ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "garden",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "garden.context_ai.ai_enabled",
                "garden.context_processors.notifications",
            ],
        },
    },
]

# Database: postgres when POSTGRES_HOST is set (compose dev, cluster),
# sqlite otherwise (tests, quick local hacking with zero setup).
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "NAME": os.environ.get("POSTGRES_DB", "yardwise"),
            "USER": os.environ.get("POSTGRES_USER", "yardwise"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "dev.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# Authentik SSO via ingress forward-auth (issue #3), matching the vinyl
# pattern: Traefik sends every request through Authentik, which injects
# X-authentik-username. AUTH_TRUST_PROXY_HEADER must be set ONLY where that
# ingress is the sole route to the app (the cluster) - trusting the header on
# a directly reachable server would let anyone impersonate anyone. Local dev
# and tests leave it unset and use Django's session login / admin.
AUTH_TRUST_PROXY_HEADER = env_bool("AUTH_TRUST_PROXY_HEADER", False)
if AUTH_TRUST_PROXY_HEADER:
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
        "config.auth.AuthentikRemoteUserMiddleware",
    )
    AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.RemoteUserBackend"]
LOGIN_URL = "/admin/login/"

LOGIN_REDIRECT_URL = "/"
# Behind forward-auth, clearing only the Django session would re-authenticate
# instantly from the proxy header. Hand off to Authentik's supported OIDC
# end-session endpoint so the upstream session ends too. Keep this configurable
# in case the authentication host or application slug changes later.
AUTHENTIK_LOGOUT_URL = os.environ.get(
    "AUTHENTIK_LOGOUT_URL",
    "https://auth.meklab.net/application/o/yardwise/end-session/",
)
LOGOUT_REDIRECT_URL = (
    AUTHENTIK_LOGOUT_URL if AUTH_TRUST_PROXY_HEADER else "/"
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TZ", "America/Los_Angeles")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
# Media lives in Garage S3 when configured (stateless pod -> zero-downtime
# deploys, #28); plain filesystem otherwise (dev, and the pre-S3 fallback).
YARDWISE_S3_BUCKET = os.environ.get("YARDWISE_S3_BUCKET", "")
if YARDWISE_S3_BUCKET:
    _default_storage = {
        "BACKEND": "config.media_storage.GardenMediaStorage",
        "OPTIONS": {
            "bucket_name": YARDWISE_S3_BUCKET,
            "endpoint_url": os.environ.get("YARDWISE_S3_ENDPOINT",
                                           "http://garage-s3.infra.svc.cluster.local:3900"),
            "region_name": os.environ.get("YARDWISE_S3_REGION", "meklab"),
            "access_key": os.environ.get("YARDWISE_S3_ACCESS_KEY", ""),
            "secret_key": os.environ.get("YARDWISE_S3_SECRET_KEY", ""),
            "addressing_style": "path",
        },
    }
else:
    _default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": _default_storage,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Uploaded photos. In the cluster this is the Longhorn PVC mount.
MEDIA_URL = "media/"
MEDIA_ROOT = os.environ.get("YARDWISE_MEDIA_ROOT", str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
