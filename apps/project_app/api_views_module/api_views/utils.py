#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common utilities for project API views."""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from apps.project_app.models import Project

logger = logging.getLogger(__name__)


def get_project_with_access(
    request, username: str, slug: str
) -> tuple[Project | None, JsonResponse | None]:
    """
    Get project and check if user has access.

    Returns:
        Tuple of (project, None) if access granted, or (None, error_response) if denied.
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
        or project.visibility == "public"
    )

    if not has_access:
        return None, JsonResponse(
            {"success": False, "error": "Permission denied"}, status=403
        )

    return project, None


def error_response(message: str, status: int = 400) -> JsonResponse:
    """Return a JSON error response."""
    return JsonResponse({"success": False, "error": message}, status=status)


# EOF
