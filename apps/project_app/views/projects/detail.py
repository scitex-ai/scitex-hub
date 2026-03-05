#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Detail View

Display project details with GitHub-style file browser and README.
"""

from __future__ import annotations

import logging

from django.shortcuts import render

from ...decorators import project_access_required
from ...models import ProjectFork, ProjectStar, ProjectWatch
from .detail_helpers import (
    get_branches,
    get_directory_contents,
    get_readme_content,
)

logger = logging.getLogger(__name__)


@project_access_required
def project_detail(request, username, slug):
    """
    Project detail page (GitHub-style /<username>/<project>/)

    Authenticated users → rendered inside the Hub workspace frame.
    Unauthenticated users → standalone project page.
    """
    # Special case: if slug matches username, this is a bio/profile README page
    if slug == username:
        from ..users.profile import user_bio_page

        return user_bio_page(request, username)

    # project available in request.project from decorator
    project = request.project

    # Authenticated users → hub workspace with project pre-selected
    if request.user.is_authenticated:
        from apps.hub_app.views.index import build_hub_context

        context = build_hub_context(request, current_project=project)
        return render(request, "hub_app/index.html", context)

    # Check for port proxy request (e.g., ?port=6006)
    port_param = request.GET.get("port")
    if port_param:
        try:
            port = int(port_param)
            from ...utils.port_proxy import get_port_proxy_manager

            proxy_manager = get_port_proxy_manager()
            return proxy_manager.proxy_request(request, port)
        except ValueError:
            from django.http import HttpResponse

            return HttpResponse(
                f"Invalid port parameter: {port_param}",
                status=400,
                content_type="text/plain",
            )
        except Exception as e:
            from django.http import HttpResponse

            logger.error(f"Port proxy error: {e}", exc_info=True)
            return HttpResponse(
                f"Proxy error: {str(e)}", status=500, content_type="text/plain"
            )

    mode = request.GET.get("mode", "overview")
    view = request.GET.get("view", "default")

    # Track last active repository — only for projects the user owns
    if request.user.is_authenticated and hasattr(request.user, "profile"):
        if project.owner_id == request.user.id:
            if request.user.profile.last_active_repository != project:
                request.user.profile.last_active_repository = project
                request.user.profile.save(update_fields=["last_active_repository"])

    # Handle concatenated view
    if view == "concatenated":
        from ..api_views import api_concatenate_directory

        return api_concatenate_directory(request, username, slug, "")

    # Route to appropriate module based on mode
    if mode == "writer":
        from apps.writer_app import views as writer_views

        return writer_views.project_writer(request, project.id)
    elif mode == "code":
        from apps.console_app import views as code_views

        return code_views.project_code(request, project.id)
    elif mode == "viz":
        from apps.viz_app import views as viz_views

        return viz_views.project_viz(request, project.id)

    # Default mode: overview - GitHub-style file browser with README
    # Get project directory and file list
    is_remote_type = project.project_type in ("remote", "trip")

    project_path = _get_project_path(project)

    # Get directory contents and README (skip git info for remote/trip)
    if project_path and project_path.exists():
        files, dirs = get_directory_contents(project_path, skip_git=is_remote_type)
        readme_content, readme_html = get_readme_content(project_path)
    else:
        files, dirs = [], []
        readme_content, readme_html = None, None

    # Get branches (skip for remote/trip — no local .git)
    current_branch = project.current_branch or "develop"
    if is_remote_type:
        branches = []
    else:
        branches, current_branch = get_branches(project_path, current_branch)

    # Get social interaction counts
    watch_count = ProjectWatch.objects.filter(project=project).count()
    star_count = ProjectStar.objects.filter(project=project).count()
    fork_count = ProjectFork.objects.filter(original_project=project).count()

    # Check if current user has watched/starred the project
    is_watching = False
    is_starred = False
    if request.user.is_authenticated:
        is_watching = ProjectWatch.objects.filter(
            user=request.user, project=project
        ).exists()
        is_starred = ProjectStar.objects.filter(
            user=request.user, project=project
        ).exists()

    # Get Gitea URLs for clone button (only for local projects)
    gitea_https_url = ""
    gitea_ssh_url = ""
    download_zip_url = ""
    if not is_remote_type:
        from django.conf import settings

        gitea_url = getattr(settings, "SCITEX_CLOUD_GITEA_URL", "http://127.0.0.1:3000")
        gitea_ssh_domain = getattr(settings, "SCITEX_CLOUD_GIT_DOMAIN", "127.0.0.1")
        gitea_ssh_port = getattr(settings, "SCITEX_CLOUD_GITEA_SSH_PORT", "2222")

        gitea_https_url = f"{gitea_url}/{project.owner.username}/{project.slug}.git"
        gitea_ssh_url = f"ssh://git@{gitea_ssh_domain}:{gitea_ssh_port}/{project.owner.username}/{project.slug}.git"
        download_zip_url = f"{gitea_url}/{project.owner.username}/{project.slug}/archive/{current_branch}.zip"

    context = {
        "project": project,
        "user": request.user,
        "directories": dirs,
        "files": files,
        "readme_content": readme_content,
        "readme_html": readme_html,
        "mode": mode,
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

    # Check dev-install status for app repos
    if request.user.is_authenticated and project.is_app:
        from apps.apps_app.models import DevInstallation

        context["is_dev_installed"] = DevInstallation.objects.filter(
            user=request.user,
            source_owner=project.owner.username,
            source_repo=project.slug,
        ).exists()

    return render(request, "project_app/repository/browse.html", context)


@project_access_required
def project_tree_or_blob(request, username, slug, branch=None, path=None):
    """GitHub-style tree/blob URLs — render via hub for authenticated users."""
    project = request.project
    if request.user.is_authenticated:
        from apps.hub_app.views.index import build_hub_context

        context = build_hub_context(request, current_project=project)
        return render(request, "hub_app/index.html", context)
    # Unauthenticated: fall through to standalone project detail
    return project_detail(request, username, slug)


def _get_project_path(project):
    """Get filesystem path for any project type via ProjectServiceManager."""
    if project.project_type == "trip":
        # TRIP has no local path — return None
        return None
    try:
        from apps.project_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        return ProjectServiceManager(project).get_project_path()
    except Exception as exc:
        logger.warning(f"Could not resolve project path: {exc}")
        return None


# EOF
