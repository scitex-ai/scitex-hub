#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/api/repository_health.py
# ----------------------------------------
"""
Repository Health Management API Views

This module contains API endpoints for repository health checking,
cleanup, synchronization, and restoration operations.
"""

from __future__ import annotations
import json
import logging

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Repository Health Management APIs
# ============================================================================


@login_required
def api_repository_health(request, username):
    """
    API endpoint to check repository health for a user.

    GET: Returns list of all repository health issues and statistics
    """
    if request.method != "GET":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    # Only allow users to check their own repository health
    user = get_object_or_404(User, username=username)
    if user != request.user and not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    try:
        from apps.project_app.services.repository_health_service import (
            RepositoryHealthChecker,
        )

        checker = RepositoryHealthChecker(user)
        issues, stats = checker.check_all_repositories()

        return JsonResponse(
            {
                "success": True,
                "stats": stats,
                "issues": [issue.to_dict() for issue in issues],
            }
        )

    except Exception as e:
        logger.error(f"Error checking repository health: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def api_repository_cleanup(request, username):
    """
    API endpoint to cleanup orphaned Gitea repositories.

    POST: Delete an orphaned repository (requires confirmation)
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    # Only allow users to manage their own repositories
    user = get_object_or_404(User, username=username)
    if user != request.user and not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
        gitea_name = data.get("gitea_name", "").strip()

        if not gitea_name:
            return JsonResponse(
                {"success": False, "error": "Repository name required"}, status=400
            )

        from apps.project_app.services.repository_health_service import (
            RepositoryHealthChecker,
        )

        checker = RepositoryHealthChecker(user)
        success, message = checker.delete_orphaned_repository(gitea_name)

        return JsonResponse(
            {
                "success": success,
                "message": message,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error during repository cleanup: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def api_repository_sync(request, username):
    """
    API endpoint to sync a repository.

    POST: Sync project with Gitea (re-clone if needed)
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    # Only allow users to manage their own repositories
    user = get_object_or_404(User, username=username)
    if user != request.user and not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
        project_slug = data.get("project_slug", "").strip()

        if not project_slug:
            return JsonResponse(
                {"success": False, "error": "Project slug required"}, status=400
            )

        from apps.project_app.services.repository_health_service import (
            RepositoryHealthChecker,
        )

        checker = RepositoryHealthChecker(user)
        success, message = checker.sync_repository(project_slug)

        return JsonResponse(
            {
                "success": success,
                "message": message,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error during repository sync: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def api_repository_restore(request, username):
    """
    API endpoint to restore an orphaned Gitea repository.

    Recovers a project by creating a Django project linked to an orphaned
    Gitea repository. This restores the full 1:1:1 mapping.

    POST: Restore orphaned repository as a new project
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    # Only allow users to manage their own repositories
    user = get_object_or_404(User, username=username)
    if user != request.user and not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
        gitea_name = data.get("gitea_name", "").strip()
        project_name = data.get("project_name", "").strip()

        if not gitea_name:
            return JsonResponse(
                {"success": False, "error": "Repository name required"}, status=400
            )

        # If no project name provided, use the gitea_name
        if not project_name:
            project_name = gitea_name

        from apps.project_app.services.repository_health_service import (
            RepositoryHealthChecker,
        )

        checker = RepositoryHealthChecker(user)
        success, message, project_id = checker.restore_orphaned_repository(
            gitea_name, project_name
        )

        return JsonResponse(
            {
                "success": success,
                "message": message,
                "project_id": project_id,  # Return project ID for redirect
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error during repository restore: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
