#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/project/__init__.py
"""SciTeX Hub project management.

Project CRUD (Python API):
    from scitex_hub.project import project_list, project_create

    projects = project_list()
    new = project_create("my-project", description="My research")

    # Create as an app project (the agent-programmatic publish flow).
    app = project_create("my-tool", category="app")
    # -> name becomes "my-tool_app" (auto-suffix), is_app=True.

Sandboxed file-operation handlers (async, used by MCP tools) live in
:mod:`scitex_hub.project._mcp.handlers`.
"""

from __future__ import annotations

from .._mcp_tools.api import _make_request

#: Top-level project categories. Currently only ``"app"`` adds non-default
#: semantics (sets ``is_app=True`` server-side + auto-suffixes the name with
#: ``_app`` if missing). ``"project"`` is the default research-project shape
#: and adds no extra fields — listed here so the API surface is closed and
#: ``--category`` can be exhaustively validated CLI-side.
PROJECT_CATEGORIES: tuple[str, ...] = ("project", "app")

#: Suffix appended to app-project names when ``category="app"`` and the
#: name doesn't already end with it. Mirrors the operator-12845 directive
#: ("the project NAME likely needs an 'app' SUFFIX").
APP_NAME_SUFFIX = "_app"


def _apply_app_suffix(name: str) -> str:
    """Return ``name`` with ``_app`` appended unless already present.

    The check is suffix-only (not substring) so e.g. ``my_app_repo`` stays
    untouched and only ``my_app`` round-trips through unchanged.
    """
    if name.endswith(APP_NAME_SUFFIX):
        return name
    return f"{name}{APP_NAME_SUFFIX}"


def project_list() -> list[dict]:
    """List all projects owned by the authenticated user.

    Returns:
        List of project dicts with id, name, description, created_at, updated_at.
    """
    result = _make_request("GET", "/api/v1/projects/")
    if result.get("success"):
        return result.get("projects", [])
    raise RuntimeError(result.get("error", "Failed to list projects"))


def project_create(
    name: str,
    description: str = "",
    template: str = "scitex_minimal",
    *,
    category: str = "project",
    app_category: str | None = None,
    request_fn=None,
) -> dict:
    """Create a new SciTeX Hub project.

    Args:
        name: Project name. When ``category="app"`` and the name does not
            already end with ``_app``, the suffix is appended automatically
            (operator-12845 convention) before the server call.
        description: Optional description.
        template: Template ID (default: scitex_minimal).
        category: Top-level project category. One of
            :data:`PROJECT_CATEGORIES`. ``"app"`` marks the new project as
            an app plugin (sets ``is_app=True`` server-side) — does NOT
            submit it to the registry; that's a separate
            :mod:`scitex_hub.appmaker` ``publish`` call.
        app_category: Optional app sub-category (writing, visualization,
            data, analysis, reference, utility, other). Only used when
            ``category="app"``; ignored otherwise. The sub-category can
            also be left blank at create time and filled in at
            ``app submit`` time.
        request_fn: Optional dependency-injection seam for the HTTP
            transport. Defaults to the module-level
            :func:`_make_request`. Tests inject a hand-rolled fake to
            avoid talking to a live server; production callers leave
            this argument unset.

    Returns:
        Dict with success, project_id, slug, url, is_app, app_category.

    Raises:
        ValueError: ``category`` not in :data:`PROJECT_CATEGORIES`.
        RuntimeError: Server-side rejection (name conflict, validation, etc.).
    """
    if category not in PROJECT_CATEGORIES:
        raise ValueError(
            f"category must be one of {PROJECT_CATEGORIES!r}, got {category!r}"
        )

    is_app = category == "app"
    if is_app:
        name = _apply_app_suffix(name)
    elif app_category:
        # Non-app project with app_category is a programming error — surface
        # rather than silently dropping the field.
        raise ValueError(
            f"app_category is only valid when category='app'; got category={category!r}"
        )

    payload: dict[str, object] = {
        "name": name,
        "description": description,
        "template": template,
        "is_app": is_app,
    }
    if is_app and app_category:
        payload["app_category"] = app_category

    do_request = request_fn if request_fn is not None else _make_request
    result = do_request("POST", "/api/v1/projects/create/", data=payload)
    if result.get("success"):
        return result
    raise RuntimeError(result.get("error", "Failed to create project"))


def project_delete(slug: str) -> bool:
    """Delete a project by slug.

    Args:
        slug: Project slug (URL-safe name).

    Returns:
        True if deleted successfully.
    """
    result = _make_request("DELETE", f"/api/v1/projects/{slug}/")
    if result.get("success"):
        return True
    raise RuntimeError(result.get("error", "Failed to delete project"))


def project_rename(slug: str, new_name: str) -> dict:
    """Rename a project.

    Args:
        slug: Current project slug.
        new_name: New project name.

    Returns:
        Dict with updated project info.
    """
    result = _make_request(
        "POST",
        f"/api/v1/projects/{slug}/rename/",
        data={"name": new_name},
    )
    if result.get("success"):
        return result
    raise RuntimeError(result.get("error", "Failed to rename project"))


# EOF
