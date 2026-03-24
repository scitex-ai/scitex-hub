#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/_mcp_tools/project_crud.py
"""Project CRUD MCP tools for AI agent."""

from __future__ import annotations

from .api import _json, _make_request


def register_project_crud_tools(mcp) -> None:
    """Register project CRUD tools with FastMCP server."""

    @mcp.tool()
    async def project_list() -> str:
        """List all projects owned by the current user.

        Returns project names, descriptions, and creation dates.
        """
        result = _make_request("GET", "/api/v1/projects/")
        return _json(result)

    @mcp.tool()
    async def project_create(
        name: str,
        description: str = "",
        template: str = "scitex_minimal",
    ) -> str:
        """Create a new SciTeX Cloud project.

        Args:
            name: Project name (will be slugified for URL).
            description: Optional project description.
            template: Template to use (default: scitex_minimal).
        """
        result = _make_request(
            "POST",
            "/api/v1/projects/create/",
            data={"name": name, "description": description, "template": template},
        )
        return _json(result)

    @mcp.tool()
    async def project_delete(slug: str) -> str:
        """Delete a project by slug.

        WARNING: This permanently deletes the project and all its files.

        Args:
            slug: Project slug (URL-safe name, e.g. "my-research").
        """
        result = _make_request("DELETE", f"/api/v1/projects/{slug}/")
        return _json(result)

    @mcp.tool()
    async def project_rename(slug: str, new_name: str) -> str:
        """Rename a project.

        Args:
            slug: Current project slug.
            new_name: New project name.
        """
        result = _make_request(
            "POST",
            f"/api/v1/projects/{slug}/rename/",
            data={"name": new_name},
        )
        return _json(result)

    @mcp.tool()
    async def project_switch(slug: str) -> str:
        """Switch the active project (navigates browser to project page).

        Only works on-site (in the web browser). Use ui_action for navigation.

        Args:
            slug: Project slug to switch to.
        """
        result = _make_request(
            "POST",
            "/llm/api/ui-action/",
            data={"action": "navigate", "url": f"/{slug}/"},
        )
        return _json(result)


# EOF
