#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Detail View

Display project details with GitHub-style file browser and README.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from ...decorators import project_access_required
from ...models import ProjectFork, ProjectStar, ProjectWatch
from ...services.project_tree_ui import (
    REPOSITORY_VIEW,
    build_project_tree_context,
    resolve_tree_path,
    wants_repository_view,
)
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

    # The Explorer/Finder-style file tree is the DEFAULT Project UI, for the
    # user's own projects and for public projects alike, signed in or not
    # (operator TODO 186/188/190-192, 2026-09-14). The GitHub-style repository
    # screen is kept, reachable with ?view=repository, and retired gradually
    # (TODO 189). Read access was enforced by @project_access_required, and
    # again by the tree/file-content APIs the page calls.
    # Any explicit ?view= (repository, concatenated) or ?mode= (writer, code,
    # viz) keeps its own screen below.
    if not request.GET.get("view") and not request.GET.get("mode"):
        return render_project_tree(request, project, username)

    # Authenticated users → hub workspace with project pre-selected
    if request.user.is_authenticated:
        # Check if this is an org-owned repo — if so, mark it so the template
        # shows the "org | project" hub mode tabs (GitHub-style).
        from apps.infra.organizations_app.models import Organization

        is_org_context = Organization.objects.filter(slug=username).exists()

        from apps.workspace.my_projects_app.views.index import build_hub_context

        context = build_hub_context(
            request, current_project=project, include_file_browser=True
        )
        if is_org_context:
            context["is_org_context"] = True
            context["org_slug"] = username
        return render(request, "my_projects_app/index.html", context)

    # NOTE: an unauthenticated `?port=` branch used to live here and forwarded
    # the request to http://127.0.0.1:<port> (CodeQL py/partial-ssrf #9385,
    # apps/infra/project_app/utils/port_proxy.py). It was removed: the branch
    # sat AFTER the is_authenticated return above, so it was reachable ONLY by
    # anonymous visitors — the check was inverted, the feature never served the
    # logged-in workspace users it was written for, and it let anyone port-scan
    # and read back localhost services in the 10000-20000 range. Nothing in the
    # product ever built a `?port=` link (workspace Jupyter/TensorBoard go
    # through console_app's own API), so this was dead code and a live SSRF.
    # Regression: tests/apps/project_app/views/projects/test_detail_port_proxy.py

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
        from apps.workspace.writer_app import views as writer_views

        return writer_views.project_writer(request, project.id)
    elif mode == "code":
        from apps.workspace.console_app import views as code_views

        return code_views.project_code(request, project.id)
    elif mode == "viz":
        from apps.workspace.figrecipe_app import views as viz_views

        return viz_views.project_viz(request, project.id)

    # Default mode: overview - GitHub-style file browser with README
    # Get project directory and file list
    is_remote_type = project.project_type == "remote"

    project_path = _get_project_path(project)

    # Get directory contents and README
    if project.project_type == "remote" and _is_trip_mode(project):
        # TRIP: fetch files from remote via SFTP
        files, dirs, readme_content, readme_html = _get_trip_contents(project)
    elif project_path and project_path.exists():
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

        gitea_url = getattr(settings, "SCITEX_HUB_GITEA_URL", "http://127.0.0.1:3000")
        gitea_ssh_domain = getattr(settings, "SCITEX_HUB_GIT_DOMAIN", "127.0.0.1")
        gitea_ssh_port = getattr(settings, "SCITEX_HUB_GITEA_SSH_PORT", "2222")

        gitea_https_url = f"{gitea_url}/{project.owner.username}/{project.slug}.git"
        gitea_ssh_url = f"ssh://git@{gitea_ssh_domain}:{gitea_ssh_port}/{project.owner.username}/{project.slug}.git"
        download_zip_url = f"{gitea_url}/{project.owner.username}/{project.slug}/archive/{current_branch}.zip"

    # Get remote config for remote projects (includes connection_mode)
    trip_config = None
    if project.project_type == "remote":
        try:
            remote_cfg = project.remote_config
            if remote_cfg.connection_mode == "trip":
                trip_config = remote_cfg
        except Exception:
            pass

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
        "trip_config": trip_config,
    }

    # Check dev-install status for app repos
    if request.user.is_authenticated and project.is_app:
        from apps.workspace.apps_app.models import DevInstallation

        context["is_dev_installed"] = DevInstallation.objects.filter(
            user=request.user,
            source_owner=project.owner.username,
            source_repo=project.slug,
        ).exists()

    return render(request, "project_app/repository/browse.html", context)


@project_access_required
def project_tree_or_blob(request, username, slug, branch=None, path=None):
    """GitHub-style /tree/<branch>/<path> URLs — the tree UI, folder expanded.

    The tree shows the project's working copy, so ``branch`` does not select
    what is listed; it is accepted so links shaped like GitHub's keep working.
    ``?view=repository`` opens the GitHub-style directory screen instead.
    """
    project = request.project
    folder = (path or "").strip("/")
    if wants_repository_view(request):
        if folder:
            detail_url = reverse(
                "project_app:detail", kwargs={"username": username, "slug": slug}
            )
            redirect_url = f"{detail_url}{quote(folder, safe='/')}/"
            if url_has_allowed_host_and_scheme(
                redirect_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(redirect_url)
            return redirect("project_app:detail", username=username, slug=slug)
        detail_url = reverse(
            "project_app:detail", kwargs={"username": username, "slug": slug}
        )
        return redirect(f"{detail_url}?view={REPOSITORY_VIEW}")
    # GitHub also serves files under /tree/: /tree/main/AGENTS.md opens the
    # file in the viewer instead of trying to expand a folder of that name.
    focus_path, open_file = resolve_tree_path(project, folder)
    return render_project_tree(
        request,
        project,
        username,
        focus_path=focus_path,
        open_file=open_file,
        repository_view_url=(
            f"/{username}/{slug}/{folder}/"
            if folder
            else f"/{username}/{slug}/?view={REPOSITORY_VIEW}"
        ),
    )


def render_project_tree(request, project, username, **tree_kwargs):
    """The one Project UI for ``project``, for any viewer with read access.

    Signed-in viewers get it inside the workspace (file tree + viewer pane,
    their projects listed alongside). Anonymous visitors — who only reach
    here for a PUBLIC project — get the same tree and viewer, read-only, on a
    standalone page: the workspace shell itself is a signed-in surface.
    """
    if request.user.is_authenticated:
        from apps.workspace.my_projects_app.views.index import render_project_tree_ui

        return render_project_tree_ui(
            request, project, url_owner=username, **tree_kwargs
        )
    context = {"current_project": project, "project": project}
    context.update(build_project_tree_context(request, project, **tree_kwargs))
    context["project_tree_public_read"] = True
    return render(request, "project_app/repository/public_tree.html", context)


def _get_trip_contents(project):
    """Fetch remote file listing for TRIP projects via SFTP.

    Returns (files, dirs, readme_content, readme_html) matching the format
    expected by browse templates — just like local projects but over SSH.
    """
    files, dirs = [], []
    readme_content, readme_html = None, None

    try:
        from ..services.trip_backend import get_trip_backend

        backend = get_trip_backend(project)
        items = backend.list_dir("")

        for item in items:
            entry = {
                "name": item["name"],
                "path": item["path"],
            }
            if item["type"] == "directory":
                dirs.append(entry)
            else:
                files.append(entry)

        # Try to read README
        for readme_name in ["README.md", "readme.md", "README", "README.rst"]:
            try:
                content = backend.read_file(readme_name)
                readme_content = content
                import markdown

                readme_html = markdown.markdown(
                    content, extensions=["fenced_code", "tables"]
                )
                break
            except Exception:
                continue

    except Exception as exc:
        logger.warning(f"TRIP file listing failed: {exc}")

    return files, dirs, readme_content, readme_html


def _is_trip_mode(project):
    """Return True if the remote project uses connection_mode='trip'."""
    try:
        return project.remote_config.connection_mode == "trip"
    except Exception:
        return False


def _get_project_path(project):
    """Get filesystem path for any project type via ProjectServiceManager."""
    if project.project_type == "remote" and _is_trip_mode(project):
        # TRIP mode has no local path — return None
        return None
    try:
        from apps.infra.project_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        return ProjectServiceManager(project).get_project_path()
    except Exception as exc:
        logger.warning(f"Could not resolve project path: {exc}")
        return None


# EOF
