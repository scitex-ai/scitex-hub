#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub app index view - Central project hub."""

import logging

from django.shortcuts import redirect, render

from apps.project_app.models import Project
from apps.project_app.services.project_utils import get_current_project

logger = logging.getLogger(__name__)


def build_hub_context(request, current_project=None):
    """Build hub-specific template context for both full page and partial views.

    When current_project is set, shows project file browser (GitHub-style).
    When no project, shows dashboard with project cards.
    """

    context = {
        "is_visitor": False,
        "module_name": "Hub",
        "module_icon": "fa-home",
        "current_project": current_project,
    }

    # Quick Reference: SSH and URL info
    host = request.get_host()
    is_dev = "127.0.0.1" in host or "localhost" in host
    ssh_hostname = "127.0.0.1" if is_dev else "ssh.scitex.ai"
    ssh_port = "2200" if is_dev else ""
    context["quick_ref"] = {
        "ssh_hostname": ssh_hostname,
        "ssh_port": ssh_port,
        "is_dev": is_dev,
        "username": request.user.username,
    }

    # Mark as demo/visitor if visitor-* or readonly-visitor
    from apps.project_app.services.visitor_pool import VisitorPool

    if request.user.username.startswith("visitor-"):
        context["is_demo"] = True
        context["is_visitor"] = True
        context["visitor_username"] = request.user.username

    if request.user.username == VisitorPool.READONLY_VISITOR_USERNAME:
        context["is_demo"] = True
        context["is_visitor"] = True
        context["is_readonly"] = True
        context["visitor_username"] = request.user.username

    # Get user's projects for overview (reusing project_app models)
    user_projects = Project.objects.filter(owner=request.user).order_by("-updated_at")[
        :6
    ]
    context["user_projects"] = user_projects
    context["projects_count"] = Project.objects.filter(owner=request.user).count()
    context["needs_project_creation"] = context["projects_count"] == 0

    # Get recent activities (reusing social_app models)
    from apps.social_app.models import Activity

    recent_activities = Activity.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:5]
    context["recent_activities"] = recent_activities

    # Set initial active tab: "projects" when a project is loaded, "me" otherwise
    context["hub_initial_mode"] = "projects" if current_project else "me"

    # Add profile context for Me tab initial render (when no project is loaded)
    if not current_project:
        from apps.social_app.models import UserFollow

        context.update(
            {
                "profile_user": request.user,
                "projects": user_projects,
                "followers_count": UserFollow.get_followers_count(request.user),
                "following_count": UserFollow.get_following_count(request.user),
                "is_own_projects": True,
                "show_account_settings": True,
            }
        )

    # When a project is selected, add file browser data
    if current_project:
        _add_file_browser_context(request, current_project, context)

        # Check dev-install status for app repos
        if request.user.is_authenticated and current_project.is_app:
            from apps.apps_app.models import DevInstallation

            context["is_dev_installed"] = DevInstallation.objects.filter(
                user=request.user,
                source_owner=current_project.owner.username,
                source_repo=current_project.slug,
            ).exists()

    return context


def index_view(request):
    """Hub main page - Central project hub with GitHub-style features.

    Layout:
    - Left sidebar: File tree (consistent with other modules)
    - Main area: Projects overview cards + Recent Activity
    - Right panel: Details/properties placeholder

    For authenticated users: loads their project + shows projects list
    For visitor users: provides demo workspace
    If visitor pool is exhausted: redirect to visitor-pool-full page
    """
    # Check if user is not authenticated (visitor allocation may have failed)
    if not request.user.is_authenticated:
        # Check if this is a browser request (has typical browser User-Agent)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        is_browser = any(
            browser in user_agent
            for browser in ["Mozilla", "Chrome", "Safari", "Firefox", "Edge", "Opera"]
        )

        if is_browser:
            # Browser request but not authenticated - visitor pool likely exhausted
            logger.info(
                "[Hub] Browser request not authenticated - redirecting to visitor-pool-full"
            )
            return redirect("public_app:visitor_pool_full")

        # Non-browser request - return empty page
        return render(
            request,
            "hub_app/index.html",
            {
                "is_visitor": True,
            },
        )

    # Handle ?view=profile&username=X — render profile inside Hub
    view_mode = request.GET.get("view", "")
    profile_username = request.GET.get("username", "")

    if view_mode == "profile" and profile_username:
        context = build_hub_context(request)
        context["hub_view_mode"] = "profile"
        context["hub_profile_username"] = profile_username
        context.update(_build_profile_context(request, profile_username))
        return render(request, "hub_app/index.html", context)

    current_project = (
        get_current_project(request, user=request.user)
        if request.user.is_authenticated
        else None
    )
    context = build_hub_context(request, current_project=current_project)
    return render(request, "hub_app/index.html", context)


def explore_view(request):
    """GET /explore/ — Hub with Explore tab pre-selected."""
    if not request.user.is_authenticated:
        return redirect("public_app:visitor_pool_full")
    context = build_hub_context(request)
    context["hub_initial_mode"] = "explore"
    return render(request, "hub_app/index.html", context)


def current_project_view(request):
    """GET /current-project/ — Hub with Current Project tab pre-selected."""
    if not request.user.is_authenticated:
        return redirect("public_app:visitor_pool_full")
    current_project = get_current_project(request, user=request.user)
    context = build_hub_context(request, current_project=current_project)
    context["hub_initial_mode"] = "projects"
    return render(request, "hub_app/index.html", context)


def _build_profile_context(request, username):
    """Build profile context for inline Hub rendering (reuses social_app)."""
    from django.contrib.auth.models import User
    from django.db import models
    from django.shortcuts import get_object_or_404

    from apps.social_app.models import UserFollow

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
    is_following = (
        UserFollow.is_following(request.user, profile_user)
        if request.user.is_authenticated
        else False
    )

    return {
        "profile_user": profile_user,
        "projects": user_projects,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
        "is_own_projects": request.user == profile_user,
    }


def _add_file_browser_context(request, project, context):
    """Add file browser data to context (reuses project_app helpers)."""
    from django.conf import settings

    from apps.project_app.models import ProjectStar, ProjectWatch
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )
    from apps.project_app.views.projects.detail_helpers import (
        get_branches,
        get_directory_contents,
        get_readme_content,
    )

    try:
        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        files, dirs = get_directory_contents(project_path)
        _, readme_html = get_readme_content(project_path)
        current_branch = project.current_branch or "develop"
        branches, current_branch = get_branches(project_path, current_branch)

        # Social counts — aggregate into fewer queries
        from django.db.models import Count

        social = Project.objects.filter(pk=project.pk).aggregate(
            watch_count=Count("project_watchers"),
            star_count=Count("project_stars_set"),
            fork_count=Count("project_forks_set"),
        )
        watch_count = social["watch_count"]
        star_count = social["star_count"]
        fork_count = social["fork_count"]
        is_watching = ProjectWatch.objects.filter(
            user=request.user, project=project
        ).exists()
        is_starred = ProjectStar.objects.filter(
            user=request.user, project=project
        ).exists()

        # Gitea URLs
        gitea_url = getattr(settings, "SCITEX_CLOUD_GITEA_URL", "http://127.0.0.1:3000")
        ssh_domain = getattr(settings, "SCITEX_CLOUD_GIT_DOMAIN", "127.0.0.1")
        ssh_port = getattr(settings, "SCITEX_CLOUD_GITEA_SSH_PORT", "2222")

        owner_name = project.owner.username
        slug = project.slug
        gitea_https_url = f"{gitea_url}/{owner_name}/{slug}.git"
        gitea_ssh_url = f"ssh://git@{ssh_domain}:{ssh_port}/{owner_name}/{slug}.git"
        download_zip_url = (
            f"{gitea_url}/{owner_name}/{slug}/archive/{current_branch}.zip"
        )

        # Open PR count for tab badge
        from apps.project_app.models import PullRequest

        open_pr_count = PullRequest.objects.filter(
            project=project, state="open"
        ).count()

        context.update(
            {
                "directories": dirs,
                "files": files,
                "readme_html": readme_html,
                "branches": branches,
                "current_branch": current_branch,
                "watch_count": watch_count,
                "star_count": star_count,
                "fork_count": fork_count,
                "is_watching": is_watching,
                "is_starred": is_starred,
                "gitea_https_url": gitea_https_url,
                "gitea_ssh_url": gitea_ssh_url,
                "download_zip_url": download_zip_url,
                "open_pr_count": open_pr_count,
            }
        )
    except Exception as e:
        logger.warning(f"[Hub] Failed to load file browser data: {e}")
        context["file_browser_error"] = str(e)


# EOF
