#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example module views — reference implementation for workspace modules.

This module demonstrates the full contract for a workspace module:
1. **registry.py** — ModuleConfig with ai_hint + accent_color
2. **skill.py** — Skill registration for LLM integration
3. **Templates** — data-module-accent on container, data-pane-type="module" on headers
4. **Context builder** — for AJAX partial loading via module tab switcher
5. **Tests** — ModuleTestMixin validates all of the above

To create your own module, copy this pattern and ensure all 5 layers exist.
"""

from __future__ import annotations

from django.shortcuts import render

from apps.project_app.services.project_utils import get_current_project


def build_example_context(request, current_project=None):
    """Build example-specific template context.

    This function is called by both:
    - index_view() for full page loads
    - workspace_module_content() for AJAX partial loads (SPA tab switching)

    The registry references this via the dotted path:
        "apps.example_app.views.build_example_context"
    """
    return {
        "current_project": current_project,
        "module_name": "Example",
        "module_description": "A reference workspace module for developers.",
        "features": [
            "ModuleConfig in registry.py (ai_hint, accent_color, icon, template)",
            "skill.py for LLM capabilities and tool prefixes",
            "data-module-accent + data-pane-type='module' in templates",
            "SPA tab switching (no page reload)",
            "AJAX partial loading for content",
            "ModuleTestMixin validates registration + hints + CSS + skill",
            "External installability via pip entry_points",
        ],
    }


def index_view(request):
    """Example module full page view."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = build_example_context(request, current_project=current_project)
    return render(request, "example_app/index.html", context)


# EOF
