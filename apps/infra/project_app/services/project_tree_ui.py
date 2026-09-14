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
- ``project_nav_projects``   -> My Projects: owned or member, never others'
                                public projects.
- ``project_tree_projects``  -> worktree pane rows (the open project nests
                                under its row).
- ``project_tree_public_read`` -> the open project is not the viewer's, so the
                                pane reads "Public Projects".
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


def is_my_project(user, project) -> bool:
    """True when ``project`` belongs in ``user``'s My Projects: owner or member.

    Visibility plays no part: a public project someone else owns is readable,
    but it is not the viewer's project (site audit 2026-09-14, D11).
    """
    if project is None or not user.is_authenticated:
        return False
    if project.owner_id == user.pk:
        return True
    return project.memberships.filter(user=user).exists()


def nav_projects(request):
    """My Projects rows: projects the viewer owns or is a member of, newest first.

    Never another user's public project — reading one does not make it yours.
    """
    if not request.user.is_authenticated:
        return []
    from django.db.models import Q

    from apps.infra.project_app.models import Project

    return list(
        Project.objects.filter(
            Q(owner=request.user) | Q(memberships__user=request.user)
        )
        .distinct()
        .select_related("owner")
        .order_by("-updated_at")[:MAX_NAV_PROJECTS]
    )


def tree_projects(request, current_project, my_projects):
    """Rows for the worktree pane, and whether it reads as Public Projects.

    The open project always has a row — its file tree nests under it. When it
    is the viewer's own (or they are a member), the pane is My Projects with
    it among the rest. When it is not — someone else's public project, or any
    project for an anonymous visitor — the pane is Public Projects holding just
    that project, so My Projects never lists what the viewer does not own.
    """
    if current_project is None:
        return my_projects, False
    if not is_my_project(request.user, current_project):
        return [current_project], True
    if all(p.pk != current_project.pk for p in my_projects):
        return [current_project, *my_projects], False
    return my_projects, False


def resolve_tree_path(project, path: str) -> tuple[str, str]:
    """Split a /tree/<branch>/<path> target into (focus folder, open file).

    GitHub serves a file under /tree/ too, so a link like
    /tree/main/AGENTS.md must open that file rather than try to expand a folder
    named AGENTS.md (site audit 2026-09-14, D12). Anything that is not an
    existing regular file inside the project stays a folder focus.
    """
    path = (path or "").strip("/")
    if not path or getattr(project, "project_type", "") == "remote":
        return path, ""
    try:
        from apps.infra.project_app.services.filesystem.permissions import (
            validate_path_in_project,
        )
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        root = get_project_filesystem_manager(project.owner).get_project_root_path(
            project
        )
        if root is None:
            return path, ""
        target = root / path
        if validate_path_in_project(root, target) and target.is_file():
            return "", path
    except (OSError, ValueError) as exc:
        logger.debug("resolve_tree_path(%s, %r): %s", project, path, exc)
    return path, ""


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
    my_projects = nav_projects(request)
    pane_projects, pane_is_public = tree_projects(request, current_project, my_projects)
    return {
        "project_tree_ui": True,
        # My Projects (module pane list): owned or member only.
        "project_nav_projects": my_projects,
        # Worktree pane rows; the pane reads "Public Projects" when the open
        # project is not the viewer's.
        "project_tree_projects": pane_projects,
        "project_tree_public_read": pane_is_public,
        "project_tree_can_write": can_write,
        "project_tree_is_empty": (
            project_is_empty(current_project) if current_project is not None else False
        ),
        "tree_focus_path": focus_path.strip("/"),
        "tree_open_file": open_file.strip("/"),
        "repository_view_url": repository_view_url,
    }


# EOF
