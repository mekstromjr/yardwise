"""Expose ai_enabled to all templates (single cheap env check)."""

from . import ai


def ai_enabled(request):
    return {"ai_enabled": ai.enabled()}
