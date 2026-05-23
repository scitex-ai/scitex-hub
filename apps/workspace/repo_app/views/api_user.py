#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub User Profile API Views

User profile, avatar, account settings endpoints.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def api_me(request):
    """GET /hub/api/me/ — Own profile with account settings in sidebar."""
    from apps.infra.organizations_app.models import Organization
    from apps.infra.social_app.models import UserFollow

    user = request.user
    user_projects = Project.objects.filter(owner=user).order_by("-updated_at")[:20]
    followers_count = UserFollow.get_followers_count(user)
    following_count = UserFollow.get_following_count(user)
    organizations = Organization.objects.filter(members=user).order_by("name")

    html = render_to_string(
        "repo_app/partials/user_profile_content.html",
        {
            "profile_user": user,
            "projects": user_projects,
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following": False,
            "is_own_projects": True,
            "show_account_settings": True,
            "organizations": organizations,
        },
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["GET"])
def api_user_profile(request):
    """GET /hub/api/user-profile/?username=X — User profile inline."""
    from django.shortcuts import get_object_or_404

    from apps.infra.social_app.models import UserFollow

    username = request.GET.get("username", "")
    if not username:
        return JsonResponse(
            {"success": False, "error": "username required"}, status=400
        )

    profile_user = get_object_or_404(User, username=username)

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

    from apps.infra.organizations_app.models import Organization

    organizations = Organization.objects.filter(members=profile_user).order_by("name")

    html = render_to_string(
        "repo_app/partials/user_profile_content.html",
        {
            "profile_user": profile_user,
            "projects": user_projects,
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following": is_following,
            "is_own_projects": request.user == profile_user,
            "organizations": organizations,
        },
        request=request,
    )
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["POST"])
def api_update_about(request):
    """POST /hub/api/update-about/ — Update project description and/or topics."""
    from apps.infra.project_app.services.project_utils import get_current_project

    current_project = get_current_project(request, user=request.user)
    if not current_project:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    if current_project.owner != request.user:
        return JsonResponse(
            {"success": False, "error": "Permission denied"}, status=403
        )

    import json

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    update_fields = []
    if "description" in data:
        current_project.description = data["description"].strip()
        update_fields.append("description")
    if "topics" in data:
        current_project.topics = data["topics"].strip()
        update_fields.append("topics")

    if update_fields:
        current_project.save(update_fields=update_fields)

    return JsonResponse(
        {
            "success": True,
            "description": current_project.description,
            "topics": current_project.topics,
        }
    )


# Keep old endpoint as alias for backward compatibility
api_update_topics = api_update_about


@login_required
@require_http_methods(["POST"])
def api_avatar_upload(request):
    """POST /hub/api/avatar-upload/ — Upload avatar via AJAX."""
    from apps.infra.accounts_app.models import UserProfile

    if "avatar" not in request.FILES:
        return JsonResponse(
            {"success": False, "error": "No avatar file provided"}, status=400
        )

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.avatar = request.FILES["avatar"]
    profile.save(update_fields=["avatar"])

    return JsonResponse({"success": True, "avatar_url": profile.avatar.url})


# EOF
