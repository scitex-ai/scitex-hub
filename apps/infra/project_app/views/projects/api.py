#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/projects/api.py
# ----------------------------------------
"""
Project-related REST API endpoints

This module contains API endpoints for:
- Name availability checking
- Project CRUD operations (list, create, detail)
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from ...models import Project
from ...services.project_utils import set_current_project

# Name availability has one implementation. This module used to carry a copy
# that had already drifted from the routed one (no project_type, no check of
# the working tree); it is re-exported so existing imports keep working.
from ..api.name_availability import api_check_name_availability  # noqa: F401

logger = logging.getLogger(__name__)


# ============================================================================
# Project CRUD APIs
# ============================================================================


@login_required
@require_http_methods(["GET"])
def api_project_list(request):
    """API endpoint for project list"""
    projects = Project.objects.filter(owner=request.user).values(
        "id", "name", "description", "created_at", "updated_at"
    )
    return JsonResponse({"projects": list(projects)})


@login_required
@require_http_methods(["POST"])
def api_project_create(request):
    """API endpoint for project creation"""
    try:
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()

        if not name:
            return JsonResponse({"success": False, "error": "Project name is required"})

        # Ensure unique name
        unique_name = Project.generate_unique_name(name, request.user)

        project = Project.objects.create(
            name=unique_name,
            description=description,
            owner=request.user,
        )

        return JsonResponse(
            {
                "success": True,
                "project_id": project.pk,
                "message": f'Project "{project.name}" created successfully',
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_http_methods(["GET"])
def api_project_detail(request, pk):
    """API endpoint for project detail"""
    try:
        project = get_object_or_404(Project, pk=pk, owner=request.user)
        data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "progress": project.progress,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
        return JsonResponse({"success": True, "project": data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@ensure_csrf_cookie
@require_http_methods(["POST"])
def api_switch_active_project(request):
    """
    API endpoint to switch the active project for the current user.

    Updates user.profile.last_active_repository to keep frontend and backend in sync.
    This ensures the project selector shows the correct project across page refreshes.
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")

        if not project_id:
            return JsonResponse({"success": False, "error": "Project ID is required"})

        # Get the project and verify ownership
        project = get_object_or_404(Project, pk=project_id, owner=request.user)

        # Update the user's last active repository
        profile = request.user.profile
        profile.last_active_repository = project
        profile.save()

        # ...and the session slug, which is the OTHER place "current project"
        # is stored. Writing only the profile left the session pointing at the
        # previous project, so any reader that consults the session first saw a
        # stale answer while the header showed the new one. Both stores must
        # move together or "which project am I in" has two answers.
        set_current_project(request, project)

        logger.info(f"User {request.user.username} switched to project {project.name}")

        return JsonResponse(
            {
                "success": True,
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "slug": project.slug,
                    "owner": project.owner.username,
                },
                "message": f"Switched to project {project.name}",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error switching active project: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ============================================================================
# JWT-Compatible Project Creation API
# ============================================================================

from rest_framework.decorators import api_view, permission_classes  # noqa: E402
from rest_framework.permissions import IsAuthenticated  # noqa: E402
from rest_framework.response import Response  # noqa: E402


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_project_create_jwt(request):
    """
    JWT-authenticated project creation endpoint for CLI access.

    Accepts JSON::

        {
          "name": "my-thing",
          "description": "...",          # optional
          "visibility": "private",       # optional, "public"|"private"
          "is_app": false,               # optional, marks as app project
          "app_category": "writing"      # optional, app sub-category
        }

    The ``is_app`` flag is the agent-programmatic equivalent of the user
    selecting "this is an app project" at creation time. Setting it does
    NOT submit the project to the registry (that's a separate ``app
    submit`` call); it only marks the project so subsequent ``app
    install-dev`` / ``app submit`` calls know what to do.

    ``app_category`` is optional at creation: leaving it blank is fine
    (the value is required only when ``app submit`` is called and can be
    supplied there). Allowed values come from
    :data:`apps.workspace.apps_app.models.CATEGORY_CHOICES`.

    Returns: ``{"success": true, "project_id": ..., "slug": "...", "url": ..., "is_app": bool, "app_category": str}``.

    CSRF-exempt by design — authentication is via Bearer JWT token, not session.
    The Django signal in project_signals.py will automatically create the
    corresponding Gitea repository when the Project record is saved.
    """
    name = request.data.get("name", "").strip()
    description = request.data.get("description", "").strip()
    visibility = request.data.get("visibility", "private")
    is_app = bool(request.data.get("is_app", False))
    app_category = (request.data.get("app_category") or "").strip()

    if not name:
        return Response(
            {"success": False, "error": "Project name is required"}, status=400
        )

    # Validate visibility value
    valid_visibilities = ("public", "private")
    if visibility not in valid_visibilities:
        return Response(
            {
                "success": False,
                "error": f"visibility must be one of: {', '.join(valid_visibilities)}",
            },
            status=400,
        )

    # Validate app_category if supplied (optional even when is_app=True)
    if app_category:
        try:
            from apps.workspace.apps_app.models import CATEGORY_CHOICES
        except Exception:  # pragma: no cover — fail-open if apps_app unavailable
            CATEGORY_CHOICES = []
        valid_categories = {c[0] for c in CATEGORY_CHOICES}
        if valid_categories and app_category not in valid_categories:
            return Response(
                {
                    "success": False,
                    "error": (
                        f"app_category must be one of: "
                        f"{', '.join(sorted(valid_categories))}"
                    ),
                },
                status=400,
            )

    try:
        # Ensure unique name per user (appends suffix if duplicate)
        unique_name = Project.generate_unique_name(name, request.user)
        slug = Project.generate_unique_slug(unique_name, owner=request.user)

        create_kwargs = {
            "name": unique_name,
            "slug": slug,
            "description": description,
            "owner": request.user,
            "visibility": visibility,
            "is_app": is_app,
        }
        if app_category:
            create_kwargs["app_category"] = app_category

        project = Project.objects.create(**create_kwargs)

        project_url = f"/{request.user.username}/{project.slug}/"

        return Response(
            {
                "success": True,
                "project_id": project.pk,
                "slug": project.slug,
                "url": project_url,
                "is_app": project.is_app,
                "app_category": project.app_category or "",
                "message": f'Project "{project.name}" created successfully',
            },
            status=201,
        )

    except Exception as exc:
        logger.error(f"api_project_create_jwt error for user {request.user}: {exc}")
        return Response({"success": False, "error": str(exc)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_project_list_jwt(request):
    """JWT-authenticated project list endpoint for CLI access."""
    projects = Project.objects.filter(owner=request.user).values(
        "id", "name", "description", "created_at", "updated_at"
    )
    return Response({"projects": list(projects)})


# GET /api/me/ moved to apps.infra.accounts_app.views.me_whoami_views.api_me
# (whoami contract: opaque id, plan, key metadata; no email).


# EOF
