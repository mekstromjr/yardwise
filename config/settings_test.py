"""Test settings: identical to production settings except static files are
served unhashed (the whitenoise manifest requires a collectstatic run, which
tests neither need nor perform)."""

from .settings import *  # noqa: F401,F403

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
