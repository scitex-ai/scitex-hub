#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common utilities for issue API endpoints."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ....models import Issue
from ....utils.project_lookup import get_project_by_owner_slug


def get_project_and_issue(username: str, slug: str, issue_number: int):
    """
    Get project and issue objects or raise 404.

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)
    issue = get_object_or_404(Issue, project=project, number=issue_number)
    return project, issue


def parse_json_or_post(request) -> dict:
    """Parse request body as JSON, fallback to POST data."""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return request.POST


def error_response(message: str, status: int = 400) -> JsonResponse:
    """Return standardized error response."""
    return JsonResponse({"success": False, "error": message}, status=status)


def success_response(message: str, **extra) -> JsonResponse:
    """Return standardized success response."""
    return JsonResponse({"success": True, "message": message, **extra})


# EOF
