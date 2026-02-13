#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub API Views

Thin wrapper around project_app models and services.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.project_app.models import Project
from apps.social_app.models import Activity

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def api_projects_list(request):
    """
    GET /hub/api/projects/
    List user's projects with metadata (reusing project_app logic).
    """
    user = request.user

    # Get user's owned projects (reuse project_app queryset)
    projects = Project.objects.filter(owner=user).order_by("-updated_at")

    # Serialize projects data
    projects_data = [
        {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "description": project.description,
            "visibility": project.visibility,
            "project_type": project.project_type,
            "language": project.primary_language or "Unknown",
            "updated_at": project.updated_at.isoformat()
            if project.updated_at
            else None,
            "created_at": project.created_at.isoformat()
            if project.created_at
            else None,
            "url": f"/{user.username}/{project.slug}/",
            "stars_count": project.projectstar_set.count(),
            "watchers_count": project.projectwatch_set.count(),
            "forks_count": project.projectfork_set.filter(
                original_project=project
            ).count(),
        }
        for project in projects
    ]

    return JsonResponse(
        {
            "success": True,
            "projects": projects_data,
            "count": len(projects_data),
        }
    )


@login_required
@require_http_methods(["GET"])
def api_activity_feed(request):
    """
    GET /hub/api/activity/
    Recent activity feed (reusing social_app Activity model).
    """
    user = request.user
    limit = int(request.GET.get("limit", 10))

    # Get recent activities for the user (reuse social_app queryset)
    activities = Activity.objects.filter(user=user).order_by("-created_at")[:limit]

    # Serialize activity data
    activities_data = [
        {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "created_at": activity.created_at.isoformat(),
            "metadata": activity.metadata or {},
        }
        for activity in activities
    ]

    return JsonResponse(
        {
            "success": True,
            "activities": activities_data,
            "count": len(activities_data),
        }
    )


# EOF
