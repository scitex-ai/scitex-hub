"""Translation helpers for visitor-facing values loaded from data files."""

from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def translate_dynamic(value):
    """Translate a runtime string such as a pricing SSoT display value.

    The SSoT (pricing.json) is ENGLISH-SOURCED (2026-09-11: landing/pricing
    must render English by default, Japanese only after explicit selection).
    ``gettext`` returns the source unchanged for the active (default English)
    language and the catalog translation for any other (e.g. Japanese), so a
    single call covers both directions with no language branching.
    """
    return gettext(str(value))
