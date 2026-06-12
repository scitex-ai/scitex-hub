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

logger = logging.getLogger(__name__)


# ============================================================================
# Name Availability API
# ============================================================================


@login_required
@require_http_methods(["GET"])
def api_check_name_availability(request):
    """
    API endpoint to check if project name is available.

    Enforces strict 1:1 mapping: Local ↔ Django ↔ Gitea
    A name is only available if it's free in BOTH Django AND Gitea.
    """
    name = request.GET.get("name", "").strip()

    if not name:
        return JsonResponse({"available": False, "message": "Project name is required"})

    # Validate name using scitex.project validator
    try:
        from scitex.project import validate_name

        is_valid, error = validate_name(name)
        if not is_valid:
            return JsonResponse({"available": False, "message": error})
    except ImportError:
        # Fallback to basic validation if scitex.project not available
        pass

    # Check 1: Django database (name must be unique per user)
    exists_in_django = Project.objects.filter(name=name, owner=request.user).exists()
    if exists_in_django:
        return JsonResponse(
            {
                "available": False,
                "message": f'You already have a project named "{name}"',
            }
        )

    # Check 2: Gitea repository (enforce 1:1 mapping)
    # Generate slug to check in Gitea
    from django.utils.text import slugify

    slug = slugify(name)

    try:
        from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient

        client = GiteaClient()

        try:
            existing_repo = client.get_repository(
                owner=request.user.username, repo=slug
            )
            if existing_repo:
                # Gitea repo exists - check if it's orphaned (no Django project)
                # This is the problem: orphaned Gitea repo blocks creation
                return JsonResponse(
                    {
                        "available": False,
                        "message": f'Repository "{name}" already exists in Gitea. If this is an old project, please contact support to clean it up.',
                    }
                )
        except GiteaAPIError as e:
            # 404 means repository doesn't exist in Gitea - that's good
            if "404" in str(e) or "not found" in str(e).lower():
                pass  # Continue, name is available
            else:
                # Some other Gitea error - log it but don't block
                logger.warning(f"Gitea check failed for {name}: {e}")
                pass  # Continue, assume available
    except Exception as e:
        # If Gitea check fails entirely, log but don't block
        logger.warning(f"Gitea availability check failed: {e}")
        pass  # Continue, assume available

    return JsonResponse({"available": True, "message": f'"{name}" is available'})


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me(request):
    """Return authenticated user info (for CLI to resolve username)."""
    return Response(
        {
            "username": request.user.username,
            "email": request.user.email,
        }
    )


# EOF
