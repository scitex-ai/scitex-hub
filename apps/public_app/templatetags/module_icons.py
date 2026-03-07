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
def module_icon(name, context="tab", status="", is_dev=False, icon_fa=""):
    """
    Render the canonical icon for a workspace module, with optional status badge.

    Looks up icon from the central registry first. For dev apps (not in registry),
    pass icon_fa explicitly.

    Args:
        name: Module name (writer, scholar, vis, dev__owner__repo, etc.)
        context: 'tab' for module tab bar, 'nav' for global header nav
        status: Module status (wip, beta, deprecated) — shows badge overlay
        is_dev: True for dev-installed apps — shows DEV badge overlay
        icon_fa: Explicit FontAwesome class (used when module not in registry)

    Usage:
        {% module_icon "writer" %}
        {% module_icon "apps" "tab" "wip" %}
        {% module_icon "dev__user__repo" "tab" "" True "fas fa-puzzle-piece" %}
    """
    from apps.workspace_app.registry import get_module

    mod = get_module(name)

    # Build the bare icon HTML
    icon_html = ""
    if mod:
        if mod.icon_fa:
            css_class = "nav-icon-fa" if context == "nav" else ""
            icon_html = f'<i class="{mod.icon_fa} {css_class}"></i>'.replace(
                "  ", " "
            ).strip()
        elif context == "nav" and mod.icon_svg_nav:
            icon_html = mod.icon_svg_nav
        elif mod.icon_svg_tab:
            icon_html = mod.icon_svg_tab
    elif icon_fa:
        css_class = "nav-icon-fa" if context == "nav" else ""
        icon_html = f'<i class="{icon_fa} {css_class}"></i>'.replace("  ", " ").strip()

    if not icon_html:
        # Fallback: generic puzzle piece
        icon_html = '<i class="fas fa-puzzle-piece"></i>'

    # Determine badge
    badge_html = ""
    if is_dev:
        badge_html = (
            '<span class="module-status-badge module-status-badge--dev">DEV</span>'
        )
    elif status == "wip":
        badge_html = (
            '<span class="module-status-badge module-status-badge--wip">WIP</span>'
        )
    elif status == "beta":
        badge_html = (
            '<span class="module-status-badge module-status-badge--beta">BETA</span>'
        )
    elif status == "deprecated":
        badge_html = '<span class="module-status-badge module-status-badge--deprecated">OLD</span>'

    if badge_html:
        return mark_safe(
            f'<span class="module-icon-wrap">{icon_html}{badge_html}</span>'
        )

    return mark_safe(icon_html)
