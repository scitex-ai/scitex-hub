#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Overview View

Display user profile overview.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

from ...models import Project


def user_overview(request, username):
    """User profile overview tab"""
    user = get_object_or_404(User, username=username)
    is_own_profile = request.user.is_authenticated and request.user == user

    # Get recent activity
    recent_projects = Project.objects.filter(owner=user)
    if not is_own_profile:
        recent_projects = recent_projects.filter(visibility="public")
    recent_projects = recent_projects.order_by("-updated_at")[:6]

    # Get social stats
    from apps.infra.social_app.models import UserFollow

    followers_count = UserFollow.get_followers_count(user)
    following_count = UserFollow.get_following_count(user)
    is_following = (
        UserFollow.is_following(request.user, user)
        if request.user.is_authenticated
        else False
    )

    context = {
        "profile_user": user,
        "is_own_profile": is_own_profile,
        "recent_projects": recent_projects,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
        "active_tab": "overview",
    }
    return render(request, "project_app/users/overview.html", context)


# EOF
