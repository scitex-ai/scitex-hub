"""Translation helpers for visitor-facing values loaded from data files."""

from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def translate_dynamic(value):
    """Translate a runtime string such as a pricing SSoT display value."""
    return gettext(str(value))
