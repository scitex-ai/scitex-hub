#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/projects/api.py
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

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
        from apps.gitea_app.api_client import GiteaClient, GiteaAPIError

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

        return JsonResponse({
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "owner": project.owner.username,
            },
            "message": f"Switched to project {project.name}",
        })

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error switching active project: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
