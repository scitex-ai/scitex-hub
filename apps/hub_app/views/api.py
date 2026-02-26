#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub API Views

Thin wrapper around project_app models and services.
Browse/file endpoints are in api_browse.py.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.project_app.models import Project
from apps.social_app.models import Activity

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def api_projects_list(request):
    """GET /hub/api/projects/ — List user's projects with metadata."""
    user = request.user
    projects = Project.objects.filter(owner=user).order_by("-updated_at")

    projects_data = [
        {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "description": project.description,
            "visibility": project.visibility,
            "project_type": project.project_type,
            "language": project.primary_language or "Unknown",
            "updated_at": (
                project.updated_at.isoformat() if project.updated_at else None
            ),
            "created_at": (
                project.created_at.isoformat() if project.created_at else None
            ),
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
        {"success": True, "projects": projects_data, "count": len(projects_data)}
    )


@login_required
@require_http_methods(["GET"])
def api_activity_feed(request):
    """GET /hub/api/activity/ — Recent activity feed."""
    user = request.user
    limit = int(request.GET.get("limit", 10))
    activities = Activity.objects.filter(user=user).order_by("-created_at")[:limit]

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
        {"success": True, "activities": activities_data, "count": len(activities_data)}
    )


@login_required
@require_http_methods(["GET"])
def api_issues(request):
    """GET /hub/api/issues/?state=open — Issues list for inline rendering."""
    from apps.project_app.services.project_utils import get_current_project

    current_project = get_current_project(request, user=request.user)
    if not current_project:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    state_filter = request.GET.get("state", "open")
    issues = current_project.issues.select_related(
        "author", "milestone"
    ).prefetch_related("labels")

    if state_filter == "open":
        issues = issues.filter(state="open")
    elif state_filter == "closed":
        issues = issues.filter(state="closed")

    issues = issues.order_by("-created_at")[:50]
    open_count = current_project.issues.filter(state="open").count()
    closed_count = current_project.issues.filter(state="closed").count()

    html = render_to_string(
        "hub_app/partials/issues_content.html",
        {
            "project": current_project,
            "issues": issues,
            "open_count": open_count,
            "closed_count": closed_count,
            "state_filter": state_filter,
        },
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["GET"])
def api_pulls(request):
    """GET /hub/api/pulls/?state=open — Pull requests list for inline rendering."""
    from apps.project_app.models import PullRequest
    from apps.project_app.services.project_utils import get_current_project

    current_project = get_current_project(request, user=request.user)
    if not current_project:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    state_filter = request.GET.get("state", "open")
    queryset = PullRequest.objects.filter(project=current_project).select_related(
        "author"
    )

    if state_filter == "open":
        queryset = queryset.filter(state="open")
    elif state_filter == "closed":
        queryset = queryset.filter(state="closed")
    elif state_filter == "merged":
        queryset = queryset.filter(state="merged")

    prs = queryset.order_by("-created_at")[:50]
    open_count = PullRequest.objects.filter(
        project=current_project, state="open"
    ).count()
    closed_count = PullRequest.objects.filter(
        project=current_project, state="closed"
    ).count()
    merged_count = PullRequest.objects.filter(
        project=current_project, state="merged"
    ).count()

    html = render_to_string(
        "hub_app/partials/pulls_content.html",
        {
            "project": current_project,
            "prs": prs,
            "open_count": open_count,
            "closed_count": closed_count,
            "merged_count": merged_count,
            "state_filter": state_filter,
            "can_create": current_project.can_edit(request.user),
        },
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["GET"])
def api_settings(request):
    """GET /hub/api/settings/ — Project settings for inline rendering."""
    from apps.project_app.services.project_utils import get_current_project

    current_project = get_current_project(request, user=request.user)
    if not current_project:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    html = render_to_string(
        "hub_app/partials/settings_content.html",
        {
            "project": current_project,
            "is_owner": current_project.owner == request.user,
        },
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["POST"])
def api_select_project(request):
    """POST /hub/api/select-project/ — Select project, return workspace HTML."""
    from apps.project_app.services.project_utils import set_current_project

    from .index import _add_file_browser_context

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    project_id = data.get("project_id")
    if not project_id:
        return JsonResponse(
            {"success": False, "error": "project_id required"}, status=400
        )

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not project.can_view(request.user):
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    # Set as current project in session and profile
    set_current_project(request, project)
    if hasattr(request.user, "profile"):
        request.user.profile.last_active_repository = project
        request.user.profile.save(update_fields=["last_active_repository"])

    context = {"project": project}
    _add_file_browser_context(request, project, context)

    html = render_to_string(
        "hub_app/partials/project_workspace.html", context, request=request
    )
    return JsonResponse(
        {
            "success": True,
            "html": html,
            "project_id": project.id,
            "project_slug": project.slug,
            "owner": project.owner.username,
        }
    )


@login_required
@require_http_methods(["GET"])
def api_projects_overview(request):
    """GET /hub/api/projects-overview/ — Project cards grid HTML."""
    user_projects = Project.objects.filter(owner=request.user).order_by("-updated_at")[
        :6
    ]
    projects_count = Project.objects.filter(owner=request.user).count()

    html = render_to_string(
        "hub_app/partials/projects_overview.html",
        {"user_projects": user_projects, "projects_count": projects_count},
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["GET"])
def api_explore(request):
    """GET /hub/api/explore/?tab=repositories — Explore public repos and users."""
    tab = request.GET.get("tab", "repositories")
    context = {"tab": tab}

    if tab == "repositories":
        repositories = (
            Project.objects.filter(visibility="public")
            .annotate(star_count=Count("stars"))
            .select_related("owner")
            .order_by("-star_count", "-updated_at")[:20]
        )
        context["repositories"] = repositories
    elif tab == "users":
        users = (
            User.objects.filter(is_active=True)
            .exclude(username__startswith="visitor-")
            .annotate(
                repo_count=Count("project_app_owned_projects"),
                follower_count=Count("followers"),
            )
            .order_by("-follower_count", "-repo_count")[:20]
        )
        context["users"] = users

    html = render_to_string(
        "hub_app/partials/explore_content.html", context, request=request
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["GET"])
def api_user_profile(request):
    """GET /hub/api/user-profile/?username=ywatanabe — User profile inline."""
    from django.shortcuts import get_object_or_404

    from apps.social_app.models import UserFollow

    username = request.GET.get("username", "")
    if not username:
        return JsonResponse(
            {"success": False, "error": "username required"}, status=400
        )

    profile_user = get_object_or_404(User, username=username)

    # Filter projects based on visibility
    user_projects = Project.objects.filter(owner=profile_user)
    if request.user != profile_user:
        if request.user.is_authenticated:
            user_projects = user_projects.filter(
                models.Q(visibility="public") | models.Q(memberships__user=request.user)
            ).distinct()
        else:
            user_projects = user_projects.filter(visibility="public")

    user_projects = user_projects.order_by("-updated_at")[:20]

    followers_count = UserFollow.get_followers_count(profile_user)
    following_count = UserFollow.get_following_count(profile_user)
    is_following = UserFollow.is_following(request.user, profile_user)

    html = render_to_string(
        "hub_app/partials/user_profile_content.html",
        {
            "profile_user": profile_user,
            "projects": user_projects,
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following": is_following,
            "is_own_projects": request.user == profile_user,
        },
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


# EOF
