#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Detail View

Display project details with GitHub-style file browser and README.
"""

from __future__ import annotations
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from ...models import Project, ProjectWatch, ProjectStar, ProjectFork
from ...decorators import project_access_required
from .detail_helpers import (
    get_directory_contents,
    get_readme_content,
    get_branches,
)

logger = logging.getLogger(__name__)


@project_access_required
def project_detail(request, username, slug):
    """
    Project detail page (GitHub-style /<username>/<project>/)

    Supports mode via query parameter:
    - /<username>/<project>/ or ?mode=overview - Project dashboard
    - /<username>/<project>?mode=writer - Writer module (legacy, use /writer/)
    - /<username>/<project>?mode=code - Code module (legacy, use /code/)
    - /<username>/<project>?mode=viz - Viz module (legacy, use /viz/)
    - /<username>/<project>?port=6006 - Proxy to localhost:6006 (services)

    Note: Scholar module now only accessible via /scholar/
    """
    # Special case: if slug matches username, this is a bio/profile README page
    if slug == username:
        from ..users.profile import user_bio_page

        return user_bio_page(request, username)

    # project available in request.project from decorator
    project = request.project

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
                content_type='text/plain'
            )
        except Exception as e:
            from django.http import HttpResponse
            logger.error(f"Port proxy error: {e}", exc_info=True)
            return HttpResponse(
                f"Proxy error: {str(e)}",
                status=500,
                content_type='text/plain'
            )

    mode = request.GET.get("mode", "overview")
    view = request.GET.get("view", "default")

    # Track last active repository for this user
    if request.user.is_authenticated and hasattr(request.user, "profile"):
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
        from apps.code_app import views as code_views

        return code_views.project_code(request, project.id)
    elif mode == "viz":
        from apps.viz_app import views as viz_views

        return viz_views.project_viz(request, project.id)

    # Default mode: overview - GitHub-style file browser with README
    # Get project directory and file list
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    # Get directory contents and README
    files, dirs = get_directory_contents(project_path)
    readme_content, readme_html = get_readme_content(project_path)

    # Get branches for branch selector
    current_branch = project.current_branch or "develop"
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

    # Get Gitea URLs for clone button
    from django.conf import settings
    gitea_url = getattr(settings, 'SCITEX_CLOUD_GITEA_URL', 'http://127.0.0.1:3000')
    gitea_ssh_domain = getattr(settings, 'SCITEX_CLOUD_GIT_DOMAIN', '127.0.0.1')
    gitea_ssh_port = getattr(settings, 'SCITEX_CLOUD_GITEA_SSH_PORT', '2222')

    gitea_https_url = f"{gitea_url}/{project.owner.username}/{project.slug}.git"
    # Use SSH URI format with explicit port: ssh://user@host:port/path
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
    return render(request, "project_app/repository/browse.html", context)


# EOF
