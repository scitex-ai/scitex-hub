#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical workspace module icon definitions.
Single source of truth — use {% module_icon "writer" %} everywhere.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Badge mapping: version suffix → (CSS class, label)
_BADGE_MAP = {
    "-dev": ("module-status-badge--dev", "DEV"),
    "-alpha": ("module-status-badge--alpha", "ALPHA"),
    "-beta": ("module-status-badge--beta", "BETA"),
}


@register.simple_tag
def module_icon(name, context="tab", version="", icon_fa="", is_private=""):
    """
    Render the canonical icon for a workspace module, with version-based badge.

    Badge is derived from version suffix: -dev → DEV, -alpha → ALPHA, -beta → BETA.
    Private (non-published) apps show a PRIVATE badge.

    Args:
        name: Module name (writer, scholar, vis, dev__owner__repo, etc.)
        context: 'tab' for module tab bar, 'nav' for global header nav
        version: Version string (e.g. "0.1.0-alpha") — suffix determines badge
        icon_fa: Explicit FontAwesome class (used when module not in registry)
        is_private: If truthy, show PRIVATE badge instead of version-based badge

    Usage:
        {% module_icon "writer" %}
        {% module_icon "apps" "tab" "0.1.0-alpha" %}
        {% module_icon "dev__user__repo" "tab" "" "fas fa-puzzle-piece" "1" %}
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
        icon_html = '<i class="fas fa-puzzle-piece"></i>'

    # Derive badge: PRIVATE overrides version-based badges
    badge_html = ""
    if is_private:
        badge_html = '<span class="module-status-badge module-status-badge--private">PRIVATE</span>'
    else:
        version_str = str(version or "")
        for suffix, (css_cls, label) in _BADGE_MAP.items():
            if version_str.endswith(suffix):
                badge_html = (
                    f'<span class="module-status-badge {css_cls}">{label}</span>'
                )
                break

    if badge_html:
        return mark_safe(
            f'<span class="module-icon-wrap">{icon_html}{badge_html}</span>'
        )

    return mark_safe(icon_html)
