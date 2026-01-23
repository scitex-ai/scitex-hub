#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/api/name_availability.py
# ----------------------------------------
"""
Name Availability API Views

This module contains API endpoints for checking project name availability.
Enforces strict 1:1 mapping: Local ↔ Django ↔ Gitea.
"""

from __future__ import annotations
import logging

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


# EOF
