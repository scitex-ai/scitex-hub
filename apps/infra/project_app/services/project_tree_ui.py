#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Context for the unified Explorer/Finder-style Project UI.

Operator, 2026-09-14: My Projects and Public Projects must open the SAME file
tree, on every project entry point, so researchers meet one familiar shape
instead of a GitHub-style repository screen. The tree itself is the existing
workspace component (static/shared/ts/components/workspace-files-tree, mounted
by templates/global_base_partials/workspace_worktree_pane.html) and the file
viewer is the existing workspace viewer. This module only decides WHAT that
shell shows for a request:

- ``project_tree_ui``        -> the worktree pane renders the project list +
                                nested tree (not the bare tree).
- ``project_nav_projects``   -> the viewer's own projects, as tree rows.
- ``project_tree_can_write`` -> write actions (new file, upload, rename,
                                delete) are offered. The server already refuses
                                writes; this only stops offering them.
- ``project_tree_is_empty``  -> the "No files yet" empty state.
- ``tree_focus_path`` / ``tree_open_file`` -> /tree/ and /blob/ deep links.

Deliberately cheap: no branch list, no README render, no social counts. Those
belong to the GitHub-style repository screen (?view=repository), which is kept
reachable and retired gradually.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ?view=<this> keeps the GitHub-style repository screen (secondary link).
REPOSITORY_VIEW = "repository"

# Upper bound on project rows rendered server-side in the tree shell.
MAX_NAV_PROJECTS = 50


def wants_repository_view(request) -> bool:
    """True when the request explicitly asks for the GitHub-style screen."""
    return request.GET.get("view") == REPOSITORY_VIEW


def project_is_empty(project) -> bool:
    """True when a local project has nothing to show in the tree.

    Only the top level is listed (``.git`` ignored), so this stays O(entries at
    the root) instead of walking the project the way the tree builder does.
    Remote projects are never reported empty: listing them costs a network
    round-trip and the tree reports its own errors for them.
    """
    if getattr(project, "project_type", "") == "remote":
        return False
    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        root = get_project_filesystem_manager(project.owner).get_project_root_path(
            project
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("project_is_empty: cannot resolve root for %s: %s", project, exc)
        return False
    if not root or not root.exists():
        return True
    try:
        return not any(entry.name != ".git" for entry in root.iterdir())
    except OSError:
        return False


def nav_projects(request, current_project=None):
    """Rows for the tree shell: the viewer's own projects, newest first.

    The open project always has a row — its file tree nests under it — so a
    project the viewer does not own (someone's public project, or any project
    for an anonymous visitor) is put first.
    """
    projects = []
    if request.user.is_authenticated:
        from apps.infra.project_app.models import Project

        projects = list(
            Project.objects.filter(owner=request.user)
            .select_related("owner")
            .order_by("-updated_at")[:MAX_NAV_PROJECTS]
        )
    if current_project is not None and all(
        p.pk != current_project.pk for p in projects
    ):
        projects.insert(0, current_project)
    return projects


def build_project_tree_context(
    request,
    current_project=None,
    *,
    focus_path: str = "",
    open_file: str = "",
    repository_view_url: str = "",
) -> dict:
    """Template context that switches the worktree pane to the Project UI."""
    user = request.user
    can_write = bool(current_project is not None and current_project.can_edit(user))
    if current_project is not None and not repository_view_url:
        repository_view_url = (
            f"/{current_project.owner.username}/{current_project.slug}/"
            f"?view={REPOSITORY_VIEW}"
        )
    return {
        "project_tree_ui": True,
        "project_nav_projects": nav_projects(request, current_project),
        "project_tree_can_write": can_write,
        "project_tree_is_empty": (
            project_is_empty(current_project) if current_project is not None else False
        ),
        "tree_focus_path": focus_path.strip("/"),
        "tree_open_file": open_file.strip("/"),
        "repository_view_url": repository_view_url,
    }


# EOF
