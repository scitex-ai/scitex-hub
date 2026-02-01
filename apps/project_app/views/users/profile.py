#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Profile Views

Handle user profile and bio pages.
Also handles organization profile pages (GitHub-style).
"""

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from ...models import Project


def user_profile(request, username):
    """
    User or organization profile page (GitHub-style /<username>/ or /<org-slug>/)

    Public view - no login required (like GitHub)

    Supports tabs via query parameter:
    - /<username>/ or /<username>?tab=overview - Overview
    - /<username>?tab=repositories - Projects list
    - /<username>?tab=projects - Project boards (future)
    - /<username>?tab=stars - Starred projects
    """
    # Check if username is a reserved path
    from config.urls import RESERVED_PATHS

    if username.lower() in [path.lower() for path in RESERVED_PATHS]:
        raise Http404("This path is reserved and not a valid username")

    # First, try to find a user with this username
    try:
        user = User.objects.get(username=username)
        tab = request.GET.get("tab", "repositories")  # Default to repositories

        if tab == "repositories":
            return user_project_list(request, username)
        elif tab == "overview":
            from .overview import user_overview

            return user_overview(request, username)
        elif tab == "projects":
            from .board import user_projects_board

            return user_projects_board(request, username)
        elif tab == "stars":
            from .stars import user_stars

            return user_stars(request, username)
        else:
            # Invalid tab - redirect to repositories
            return user_project_list(request, username)
    except User.DoesNotExist:
        # Not a user, check if it's an organization
        from apps.organizations_app.models import Organization

        try:
            org = Organization.objects.get(slug=username)
            return organization_profile(request, org)
        except Organization.DoesNotExist:
            raise Http404("User or organization not found")


def organization_profile(request, org):
    """
    Organization profile page (GitHub-style /<org-slug>/)

    Shows organization info and public projects.
    """
    # Get organization's projects (via memberships or direct ownership)
    # For now, organizations don't directly own projects, but we can
    # show projects from all org members
    member_ids = org.members.values_list("id", flat=True)

    # Get projects from organization members
    org_projects = Project.objects.filter(owner_id__in=member_ids)

    # Filter by visibility for non-members
    is_member = request.user.is_authenticated and request.user in org.members.all()
    if not is_member:
        org_projects = org_projects.filter(visibility="public")

    org_projects = org_projects.order_by("-updated_at")

    # Pagination
    paginator = Paginator(org_projects, 12)
    page_number = request.GET.get("page")
    projects = paginator.get_page(page_number)

    context = {
        "organization": org,
        "projects": projects,
        "is_member": is_member,
        "is_admin": org.can_edit(request.user)
        if request.user.is_authenticated
        else False,
        "member_count": org.members.count(),
        "active_tab": "repositories",
    }

    return render(request, "organizations_app/profile.html", context)


def user_project_list(request, username):
    """List a specific user's projects (called from user_profile with tab=repositories)"""
    user = get_object_or_404(User, username=username)

    # Filter projects based on visibility and access
    user_projects = Project.objects.filter(owner=user)

    # If not the owner, only show public projects or projects where user is a collaborator
    if not (request.user.is_authenticated and request.user == user):
        if request.user.is_authenticated:
            # Show public projects + projects where user is a collaborator
            user_projects = user_projects.filter(
                models.Q(visibility="public") | models.Q(memberships__user=request.user)
            ).distinct()
        else:
            # Visitor users only see public projects
            user_projects = user_projects.filter(visibility="public")

    user_projects = user_projects.order_by("-updated_at")

    # Check if this is the current user viewing their own projects
    is_own_projects = request.user.is_authenticated and request.user == user

    # Add pagination
    paginator = Paginator(user_projects, 12)
    page_number = request.GET.get("page")
    projects = paginator.get_page(page_number)

    # Get social stats
    from apps.social_app.models import UserFollow

    followers_count = UserFollow.get_followers_count(user)
    following_count = UserFollow.get_following_count(user)
    is_following = (
        UserFollow.is_following(request.user, user)
        if request.user.is_authenticated
        else False
    )

    context = {
        "projects": projects,
        "profile_user": user,  # The user whose profile we're viewing
        "is_own_projects": is_own_projects,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
        "active_tab": "repositories",
        # Note: 'user' is automatically available as request.user in templates
        # Don't override it here - it should always be the logged-in user
    }
    return render(request, "project_app/users/projects.html", context)


def user_bio_page(request, username):
    """User bio/profile README page (GitHub-style /<username>/<username>/)"""
    user = get_object_or_404(User, username=username)

    # Get or create user profile
    from apps.accounts_app.models import UserProfile

    profile, created = UserProfile.objects.get_or_create(user=user)

    # Get user's projects
    projects = Project.objects.filter(owner=user).order_by("-updated_at")[
        :6
    ]  # Show top 6

    # Check if this is the user viewing their own profile
    is_own_profile = request.user.is_authenticated and request.user == user

    context = {
        "profile_user": user,
        "profile": profile,
        "projects": projects,
        "is_own_profile": is_own_profile,
        "total_projects": Project.objects.filter(owner=user).count(),
    }

    return render(request, "project_app/users/profile.html", context)


# EOF
