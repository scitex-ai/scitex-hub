#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notebook module views.

Thin Django wrapper — CRUD is handled by the platform DataStore REST API.
Frontend calls /platform/api/data/notebook/Experiment/ directly.
"""

from __future__ import annotations

from django.shortcuts import render

from apps.project_app.services.project_utils import get_current_project


def build_notebook_context(request, current_project=None):
    """Build notebook-specific template context."""
    return {"current_project": current_project}


def index_view(request):
    """Notebook module full page view."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = build_notebook_context(request, current_project=current_project)
    return render(request, "notebook_app/index.html", context)


# EOF
