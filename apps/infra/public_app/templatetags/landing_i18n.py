"""Translation helpers for visitor-facing values loaded from data files."""

from django import template
from django.utils.translation import get_language, gettext

register = template.Library()


@register.filter
def translate_dynamic(value):
    """Translate a runtime string such as a pricing SSoT display value."""
    text = str(value)
    if (get_language() or "").split("-", 1)[0] == "ja":
        return text
    return gettext(text)
