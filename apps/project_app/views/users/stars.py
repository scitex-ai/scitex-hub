#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Stars View

Display user's starred repositories.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.core.paginator import Paginator


def user_stars(request, username):
    """User starred repositories tab"""
    user = get_object_or_404(User, username=username)
    is_own_profile = request.user.is_authenticated and request.user == user

    # Get starred repositories
    from apps.social_app.models import RepositoryStar, UserFollow

    starred_repos = (
        RepositoryStar.objects.filter(user=user)
        .select_related("project")
        .order_by("-starred_at")
    )

    # Pagination
    paginator = Paginator(starred_repos, 12)
    page_number = request.GET.get("page")
    stars = paginator.get_page(page_number)

    # Get social stats
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
        "stars": stars,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
        "active_tab": "stars",
    }
    return render(request, "project_app/users/stars.html", context)


# EOF
