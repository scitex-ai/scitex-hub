#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified workspace views."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from apps.project_app.services.project_utils import get_current_project


def _get_writer_context(request, base_context: dict) -> dict:
    """Enrich context with Writer-specific variables."""
    from apps.writer_app.models import Manuscript

    context = {**base_context, "build_id": "unified", "document_type": "manuscript"}
    current_project = base_context.get("current_project")
    if not current_project:
        context["needs_project_creation"] = True
        return context

    context["project"] = current_project
    try:
        manuscript, _ = Manuscript.objects.get_or_create(
            project=current_project,
            defaults={
                "owner": current_project.owner,
                "title": f"{current_project.name} Manuscript",
            },
        )
        context["manuscript"] = manuscript
        context["manuscript_id"] = manuscript.id
        context["writer_initialized"] = manuscript.writer_initialized
        context["sections"] = {}
    except Exception:
        context["needs_project_creation"] = True
    return context


def _get_scholar_context(request, base_context: dict) -> dict:
    """Enrich context with Scholar-specific variables."""
    from apps.project_app.models import Project

    user_projects = []
    library_count = 0
    if request.user.is_authenticated:
        user_projects = list(
            Project.objects.filter(owner=request.user).order_by("name")
        )
        try:
            from apps.scholar_app.models import UserLibrary

            library_count = UserLibrary.objects.filter(user=request.user).count()
        except Exception:
            pass
    return {
        **base_context,
        "user_projects": user_projects,
        "library_count": library_count,
        "build_id": "unified",
    }


# Modules that support partial loading (Phase 1)
PARTIAL_MODULES = {
    "hub": "hub_app/index_partial.html",
    "scholar": "scholar_app/scholar_partial.html",
    "clew": "clew_app/index_partial.html",
    "console": "console_app/console_partial.html",
    "writer": "writer_app/writer_partial.html",
    "vis": "vis_app/vis_partial.html",
}

# All modules (including Phase 2 that navigate externally)
ALL_MODULES = [
    {
        "name": "hub",
        "label": "Hub",
        "icon": "fa-folder",
        "partial": True,
        "href": "/hub/",
    },
    {
        "name": "console",
        "label": "Console",
        "icon": "fa-terminal",
        "partial": True,
        "href": "/console/workspace/",
    },
    {
        "name": "writer",
        "label": "Writer",
        "icon": "fa-pen",
        "partial": True,
        "href": "/writer/",
    },
    {
        "name": "scholar",
        "label": "Scholar",
        "icon": "fa-book",
        "partial": True,
        "href": "/scholar/",
    },
    {
        "name": "vis",
        "label": "Vis",
        "icon": "fa-chart-bar",
        "partial": True,
        "href": "/vis/editor/",
    },
    {
        "name": "clew",
        "label": "Clew",
        "icon": "fa-project-diagram",
        "partial": True,
        "href": "/clew/",
    },
]


@login_required
def unified_index(request: HttpRequest, module: str = "hub") -> HttpResponse:
    """Render the unified workspace shell."""
    current_project = get_current_project(request, user=request.user)
    context = {
        "current_module": module,
        "current_project": current_project,
        "all_modules": ALL_MODULES,
    }
    return render(request, "unified_app/index.html", context)


@login_required
def unified_content(request: HttpRequest, module: str) -> HttpResponse:
    """Return module partial HTML for AJAX loading.

    Requires X-Unified-Module header to prevent direct access.
    """
    if request.headers.get("X-Unified-Module") != "1":
        return HttpResponseForbidden(
            "Direct access not allowed. Use AJAX with X-Unified-Module header."
        )

    template_name = PARTIAL_MODULES.get(module)
    if not template_name:
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound(
            f"Module '{module}' does not support partial loading yet."
        )

    current_project = get_current_project(request, user=request.user)
    context = {
        "current_module": module,
        "current_project": current_project,
        "project": current_project,  # browse_header.html uses {{ project }}
        "all_modules": ALL_MODULES,
    }
    if module == "scholar":
        context = _get_scholar_context(request, context)
    elif module == "writer":
        context = _get_writer_context(request, context)
    elif module in ("console", "vis"):
        if not current_project:
            context["needs_project_creation"] = True
    return render(request, template_name, context)


# EOF
