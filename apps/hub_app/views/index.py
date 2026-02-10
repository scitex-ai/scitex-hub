#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub app index view - Central project hub."""

import logging

from django.shortcuts import redirect, render

from apps.project_app.services.project_utils import get_current_project

logger = logging.getLogger(__name__)


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

    context = {
        "is_visitor": False,
        "module_name": "Hub",
        "module_icon": "fa-home",
    }

    # Mark as demo if visitor
    if request.user.username.startswith("visitor-"):
        context["is_demo"] = True
        context["visitor_username"] = request.user.username

    # Get current project from header dropdown
    current_project = get_current_project(request, user=request.user)

    if current_project:
        context["current_project"] = current_project
        context["project"] = current_project
        logger.info(
            f"[Hub] User {request.user.username} viewing project: {current_project.slug}"
        )

        # Fetch file browser data (same as Files page)
        _add_file_browser_context(request, current_project, context)
    else:
        context["needs_project_creation"] = True

    # Get user's projects for overview (reusing project_app models)
    from apps.project_app.models import Project

    user_projects = Project.objects.filter(owner=request.user).order_by("-updated_at")[
        :6
    ]
    context["user_projects"] = user_projects
    context["projects_count"] = Project.objects.filter(owner=request.user).count()

    # Get recent activities (reusing social_app models)
    from apps.social_app.models import Activity

    recent_activities = Activity.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:5]
    context["recent_activities"] = recent_activities

    return render(request, "hub_app/index.html", context)


def _add_file_browser_context(request, project, context):
    """Add file browser data to context (reuses project_app helpers)."""
    from django.conf import settings

    from apps.project_app.models import ProjectFork, ProjectStar, ProjectWatch
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

        # Social counts
        watch_count = ProjectWatch.objects.filter(project=project).count()
        star_count = ProjectStar.objects.filter(project=project).count()
        fork_count = ProjectFork.objects.filter(original_project=project).count()
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
            }
        )
    except Exception as e:
        logger.warning(f"[Hub] Failed to load file browser data: {e}")
        context["file_browser_error"] = str(e)


# EOF
