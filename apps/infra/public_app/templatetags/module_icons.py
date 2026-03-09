#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical workspace module icon builder.

Single source of truth for rendering module icons with badge overlays.

Usage in templates:
    {% load module_icons %}
    {% module_icon "writer" %}
    {% module_icon "apps" "tab" "0.1.0-alpha" %}

Usage in Python:
    from apps.infra.public_app.templatetags.module_icons import build_module_icon_html
    html = build_module_icon_html("writer", context="tab", version="0.1.0")
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Badge mapping: version suffix → (CSS class, content)
BADGE_MAP = {
    "-dev": ("module-status-badge--dev", "DEV"),
    "-alpha": ("module-status-badge--alpha", "\u03b1"),  # α
    "-beta": ("module-status-badge--beta", "\u03b2"),  # β
}


def build_module_icon_html(
    name: str,
    context: str = "tab",
    version: str = "",
    icon_fa: str = "",
    is_private: bool = False,
) -> str:
    """Build the canonical icon HTML for a workspace module.

    This is the single source of truth for module icon rendering.
    Both the template tag and Python views should call this function.

    Args:
        name: Module name (writer, scholar, vis, dev__owner__repo, etc.)
        context: 'tab' for module tab bar, 'nav' for global header nav
        version: Version string (e.g. "0.1.0-alpha") — suffix determines badge
        icon_fa: Explicit FontAwesome class (used when module not in registry)
        is_private: If True, show lock icon overlay

    Returns:
        HTML string for the icon (with badge overlay if applicable).
    """
    from apps.infra.workspace_app.registry import get_module

    mod = get_module(name)

    # 1. Build bare icon HTML
    icon_html = _resolve_icon_html(mod, context, icon_fa)

    # 2. Build badge overlay
    badge_html = _resolve_badge_html(version, is_private)

    # 3. Wrap with overlay container if badge present
    if badge_html:
        return f'<span class="module-icon-wrap">{icon_html}{badge_html}</span>'

    return icon_html


def _resolve_icon_html(mod, context: str, icon_fa: str) -> str:
    """Resolve the bare icon element (no badge)."""
    if mod:
        if mod.icon_fa:
            extra = " nav-icon-fa" if context == "nav" else ""
            return f'<i class="{mod.icon_fa}{extra}"></i>'
        if context == "nav" and mod.icon_svg_nav:
            return mod.icon_svg_nav
        if mod.icon_svg_tab:
            return mod.icon_svg_tab

    if icon_fa:
        extra = " nav-icon-fa" if context == "nav" else ""
        return f'<i class="{icon_fa}{extra}"></i>'

    return '<i class="fas fa-puzzle-piece"></i>'


def _resolve_badge_html(version: str, is_private: bool) -> str:
    """Resolve the badge overlay HTML. Private lock takes priority."""
    if is_private:
        return '<i class="fas fa-lock module-private-lock"></i>'

    version_str = str(version or "")
    for suffix, (css_cls, label) in BADGE_MAP.items():
        if version_str.endswith(suffix):
            return f'<span class="module-status-badge {css_cls}">{label}</span>'

    return ""


@register.simple_tag
def module_icon(name, context="tab", version="", icon_fa="", is_private=""):
    """Template tag — delegates to build_module_icon_html.

    Usage:
        {% module_icon "writer" %}
        {% module_icon "apps" "tab" "0.1.0-alpha" %}
        {% module_icon "dev__user__repo" "tab" "" "fas fa-puzzle-piece" "1" %}
    """
    return mark_safe(
        build_module_icon_html(
            name=name,
            context=context,
            version=str(version or ""),
            icon_fa=str(icon_fa or ""),
            is_private=bool(is_private),
        )
    )
