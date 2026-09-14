"""Translation helpers for visitor-facing values loaded from data files."""

from django import template
from django.urls import reverse
from django.utils.translation import get_language, gettext

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


@register.simple_tag
def tokushoho_url():
    """The 特商法 disclosure in the reader's language.

    Japanese readers get /tokushoho/ (the legally authoritative page); every
    other language gets the English reference version at /tokushoho-en/
    (operator 2026-09-14). Which URL is the site default is NOT decided here.
    """
    name = "tokushoho" if (get_language() or "").startswith("ja") else "tokushoho_en"
    return reverse(f"public_app:{name}")
