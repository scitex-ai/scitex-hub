#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical workspace module icon definitions.
Single source of truth — use {% module_icon "writer" %} everywhere.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def module_icon(name, context="tab"):
    """
    Render the canonical icon for a workspace module.

    Reads icon data from the central module registry (apps.workspace_app.registry).

    Args:
        name: Module name (writer, scholar, vis, console, clew, hub, tools)
        context: 'tab' for module tab bar, 'nav' for global header nav

    Usage:
        {% load module_icons %}
        {% module_icon "writer" %}          {# tab bar #}
        {% module_icon "writer" "nav" %}    {# global header #}
    """
    from apps.workspace_app.registry import get_module

    mod = get_module(name)
    if not mod:
        return mark_safe("")

    # FontAwesome icon
    if mod.icon_fa:
        css_class = "nav-icon-fa" if context == "nav" else ""
        return mark_safe(
            f'<i class="fas {mod.icon_fa} {css_class}"></i>'.replace("  ", " ").strip()
        )

    # Custom SVG icon
    if context == "nav" and mod.icon_svg_nav:
        return mark_safe(mod.icon_svg_nav)
    if mod.icon_svg_tab:
        return mark_safe(mod.icon_svg_tab)

    return mark_safe("")
