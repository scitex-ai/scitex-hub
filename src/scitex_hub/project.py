#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/project.py
"""Project CRUD — Python API for SciTeX Hub project management.

Usage:
    from scitex_hub.project import project_list, project_create

    projects = project_list()
    new = project_create("my-project", description="My research")
"""

from __future__ import annotations

from ._mcp_tools.api import _make_request


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
) -> dict:
    """Create a new SciTeX Hub project.

    Args:
        name: Project name.
        description: Optional description.
        template: Template ID (default: scitex_minimal).

    Returns:
        Dict with project_id, name, success.
    """
    result = _make_request(
        "POST",
        "/api/v1/projects/create/",
        data={"name": name, "description": description, "template": template},
    )
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
