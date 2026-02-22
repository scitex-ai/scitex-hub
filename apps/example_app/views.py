#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example module views — reference implementation for workspace modules.

This module demonstrates the minimal pattern for a workspace module:
1. A full-page view that renders with global_base.html
2. A context builder for AJAX partial loading via the module tab switcher

To create your own module, copy this pattern and register in registry.py.
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
            "Centralized registration via registry.py",
            "SPA tab switching (no page reload)",
            "AJAX partial loading for content",
            "Inline module tests via ModuleTestMixin",
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
