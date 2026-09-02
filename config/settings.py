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


# No hardcoded fallback key: unset means an ephemeral random key (fine for
# tests/local hacking - sessions reset on restart). Production must set
# DJANGO_SECRET_KEY (from Vault via ESO); if it goes missing there, sessions
# breaking loudly on every restart beats running on a known key silently.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or get_random_secret_key()
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

# Authentik OIDC SSO (issue #3). Enabled only when a client id is configured,
# so local dev and tests fall back to Django's session login / admin.
OIDC_ENABLED = bool(os.environ.get("OIDC_RP_CLIENT_ID"))
if OIDC_ENABLED:
    INSTALLED_APPS.append("mozilla_django_oidc")
    AUTHENTICATION_BACKENDS = [
        "mozilla_django_oidc.auth.OIDCAuthenticationBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]
    OIDC_RP_CLIENT_ID = os.environ["OIDC_RP_CLIENT_ID"]
    OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_RP_CLIENT_SECRET", "")
    OIDC_RP_SIGN_ALGO = "RS256"
    _oidc_base = os.environ.get("OIDC_BASE_URL", "").rstrip("/")
    OIDC_OP_AUTHORIZATION_ENDPOINT = f"{_oidc_base}/authorize/"
    OIDC_OP_TOKEN_ENDPOINT = f"{_oidc_base}/token/"
    OIDC_OP_USER_ENDPOINT = f"{_oidc_base}/userinfo/"
    OIDC_OP_JWKS_ENDPOINT = f"{_oidc_base}/jwks/"
    LOGIN_URL = "oidc_authentication_init"
else:
    LOGIN_URL = "/admin/login/"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TZ", "America/Los_Angeles")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
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
