#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/project_crud.py
"""Project CRUD MCP tools for AI agent."""

from __future__ import annotations

from .api import _json, _make_request


def register_project_crud_tools(mcp) -> None:
    """Register project CRUD tools with FastMCP server."""

    @mcp.tool()
    async def project_list() -> str:
        """Use when the user asks to list SciTeX Cloud projects, see what projects they own, or enumerate workspaces; replaces `scitex-cloud project list` CLI invocations and raw HTTP calls to /api/v1/projects/."""
        result = _make_request("GET", "/api/v1/projects/")
        return _json(result)

    @mcp.tool()
    async def project_create(
        name: str,
        description: str = "",
        template: str = "scitex_minimal",
    ) -> str:
        """Use when the user asks to create a new SciTeX Cloud project, start a new workspace, or scaffold from a template; replaces `scitex-cloud project create` CLI invocations and raw HTTP calls to /api/v1/projects/create/.

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
        """Use when the user asks to delete, remove, or destroy a SciTeX Cloud project (by slug); replaces `scitex-cloud project delete <slug>` CLI invocations. WARNING: permanently deletes the project and all its files.

        Args:
            slug: Project slug (URL-safe name, e.g. "my-research").
        """
        result = _make_request("DELETE", f"/api/v1/projects/{slug}/")
        return _json(result)

    @mcp.tool()
    async def project_rename(slug: str, new_name: str) -> str:
        """Use when the user asks to rename a SciTeX Cloud project or change its display name; replaces `scitex-cloud project rename <slug> <new-name>` CLI invocations.

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
        """Use when the user asks to switch to a different SciTeX Cloud project or open a project page; replaces `scitex-cloud project switch <slug>` CLI invocations. Only works on-site (navigates the browser via ui-action).

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
