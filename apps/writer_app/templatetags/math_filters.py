"""Math filters for Django templates."""

from django import template

register = template.Library()


@register.filter
def abs_value(value):
    """Return absolute value of a number."""
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value
