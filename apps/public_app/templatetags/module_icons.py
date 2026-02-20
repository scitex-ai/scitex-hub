#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical workspace module icon definitions.
Single source of truth — use {% module_icon "writer" %} everywhere.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_CLEW_SVG_NAV = (
    '<svg class="nav-icon-svg" viewBox="0 0 100 100" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
    '<circle cx="50" cy="50" r="40" stroke="currentColor" stroke-width="5"/>'
    '<line x1="10" y1="50" x2="90" y2="50" stroke="currentColor" stroke-width="4.5"/>'
    '<line x1="13" y1="35" x2="87" y2="35" stroke="currentColor" stroke-width="4"/>'
    '<line x1="13" y1="65" x2="87" y2="65" stroke="currentColor" stroke-width="4"/>'
    '<path d="M30 12 Q70 30 70 50 Q70 70 30 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<path d="M70 12 Q30 30 30 50 Q30 70 70 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<line x1="85" y1="82" x2="95" y2="95" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/>'
    "</svg>"
)

_CLEW_SVG_TAB = (
    '<svg class="tab-icon-svg" viewBox="0 0 100 100" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" width="16" height="16" style="flex-shrink:0">'
    '<circle cx="50" cy="50" r="40" stroke="currentColor" stroke-width="5"/>'
    '<line x1="10" y1="50" x2="90" y2="50" stroke="currentColor" stroke-width="4.5"/>'
    '<line x1="13" y1="35" x2="87" y2="35" stroke="currentColor" stroke-width="4"/>'
    '<line x1="13" y1="65" x2="87" y2="65" stroke="currentColor" stroke-width="4"/>'
    '<path d="M30 12 Q70 30 70 50 Q70 70 30 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<path d="M70 12 Q30 30 30 50 Q30 70 70 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<line x1="85" y1="82" x2="95" y2="95" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/>'
    "</svg>"
)

# Canonical icon definitions — ground truth for ALL templates
_MODULE_ICONS = {
    "writer": {"fa": "fa-pen"},
    "scholar": {"fa": "fa-graduation-cap"},
    "vis": {"fa": "fa-chart-line"},
    "console": {"fa": "fa-terminal"},
    "clew": {"nav_svg": _CLEW_SVG_NAV, "tab_svg": _CLEW_SVG_TAB},
    "hub": {"fa": "fa-project-diagram"},
    "tools": {"fa": "fa-tools"},
}


@register.simple_tag
def module_icon(name, context="tab"):
    """
    Render the canonical icon for a workspace module.

    Args:
        name: Module name (writer, scholar, vis, console, clew, hub, tools)
        context: 'tab' for module tab bar, 'nav' for global header nav

    Usage:
        {% load module_icons %}
        {% module_icon "writer" %}          {# tab bar #}
        {% module_icon "writer" "nav" %}    {# global header #}
    """
    icon = _MODULE_ICONS.get(name)
    if not icon:
        return mark_safe("")
    if "fa" in icon:
        css_class = "nav-icon-fa" if context == "nav" else ""
        return mark_safe(
            f'<i class="fas {icon["fa"]} {css_class}"></i>'.replace("  ", " ").strip()
        )
    # SVG (Clew)
    if context == "nav":
        return mark_safe(icon["nav_svg"])
    return mark_safe(icon["tab_svg"])
