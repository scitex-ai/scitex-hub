#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Projects Board View

Display user project boards (placeholder for future implementation).
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User


def user_projects_board(request, username):
    """User project boards tab (placeholder for future implementation)"""
    user = get_object_or_404(User, username=username)
    is_own_profile = request.user.is_authenticated and request.user == user

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
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
        "active_tab": "projects",
    }
    return render(request, "project_app/users/board.html", context)


# EOF
