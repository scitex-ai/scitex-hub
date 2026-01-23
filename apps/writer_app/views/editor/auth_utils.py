#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Authentication utilities for Writer API views.

Handles both authenticated users and visitor visitors with demo projects.
"""

from functools import wraps
from django.http import JsonResponse
from apps.project_app.models import Project
import logging

logger = logging.getLogger(__name__)


def api_login_optional(view_func):
    """Decorator that allows both authenticated and visitor users to access API endpoints.

    For authenticated users: validates project ownership
    For visitor users: validates visitor project session

    Returns JSON error (not HTML redirect) if authentication/authorization fails.
    """

    @wraps(view_func)
    def wrapper(request, project_id, *args, **kwargs):
        # Try to get the project
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": f"Project {project_id} not found"},
                status=404,
            )

        # Check authentication/authorization
        if request.user.is_authenticated:
            # Check if this is a visitor user
            is_visitor = request.user.username.startswith("visitor-")

            if is_visitor:
                # Visitor users can only access their assigned project
                from apps.project_app.services.visitor_pool import VisitorPool
                visitor_project_id = request.session.get(VisitorPool.SESSION_KEY_PROJECT_ID)
                if visitor_project_id and int(visitor_project_id) == int(project_id):
                    # Visitor accessing their assigned project - allow
                    pass
                elif project.owner == request.user:
                    # Visitor owns this project - allow
                    pass
                else:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "Visitors can only access their assigned project",
                        },
                        status=403,
                    )
            else:
                # Regular authenticated user - verify ownership or access
                if project.owner != request.user:
                    # Check if user has access through team/collaboration
                    if not project.team_members.filter(id=request.user.id).exists():
                        return JsonResponse(
                            {
                                "success": False,
                                "error": "You don't have access to this project",
                            },
                            status=403,
                        )
        else:
            # Visitor user - verify visitor pool session
            visitor_project_id = request.session.get("visitor_project_id")
            visitor_user_id = request.session.get("visitor_user_id")

            # Debug logging
            logger.info(
                f"[Auth] Visitor session check: visitor_project_id={visitor_project_id} (type={type(visitor_project_id).__name__}), project_id={project_id} (type={type(project_id).__name__})"
            )

            # Type-safe comparison (handle int/str mismatches)
            if not visitor_project_id or int(visitor_project_id) != int(project_id):
                logger.warning(
                    f"[Auth] Visitor session validation failed: visitor_project_id={visitor_project_id}, project_id={project_id}"
                )
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Invalid visitor session. Please refresh the page.",
                    },
                    status=403,
                )

            if not visitor_user_id:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Visitor user not found in session. Please refresh the page.",
                    },
                    status=403,
                )

            # Verify the visitor user owns the project (type-safe comparison)
            if int(project.owner_id) != int(visitor_user_id):
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Project does not belong to visitor user.",
                    },
                    status=403,
                )

        # Call the original view with the validated project
        return view_func(request, project_id, *args, **kwargs)

    return wrapper


def get_user_for_request(request, project_id):
    """Get the effective user for a request (authenticated user or visitor user).

    Returns:
        tuple: (user, is_visitor)
    """
    if request.user.is_authenticated:
        return request.user, False
    else:
        # Get visitor user from session
        from django.contrib.auth.models import User

        visitor_user_id = request.session.get("visitor_user_id")
        if not visitor_user_id:
            logger.warning(
                f"[Auth] No visitor_user_id in session for project {project_id}"
            )
            return None, False

        try:
            user = User.objects.get(id=visitor_user_id)
            return user, True
        except User.DoesNotExist:
            logger.error(f"[Auth] Visitor user {visitor_user_id} not found")
            return None, False
