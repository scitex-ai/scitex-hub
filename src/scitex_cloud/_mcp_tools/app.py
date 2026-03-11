#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/_mcp_tools/app.py
"""App management MCP tools — mirrors CLI commands for AI-driven app control."""

from __future__ import annotations

from .api import _json


def register_app_tools(mcp) -> None:
    """Register app management tools with FastMCP server."""

    @mcp.tool()
    async def app_get_current() -> str:
        """Get the name of the currently active SciTeX app.

        Returns the SCITEX_CURRENT_APP environment variable value,
        or empty string if not set.
        """
        from scitex_cloud.appmaker import get_current

        name = get_current()
        return _json({"success": True, "current_app": name})

    @mcp.tool()
    async def app_switch_to(app_name: str) -> str:
        """Switch the active SciTeX app.

        Sets the SCITEX_CURRENT_APP environment variable.

        Args:
            app_name: Name of the app to switch to (e.g. "writer", "scholar").
        """
        from scitex_cloud.appmaker import switch_to

        switch_to(app_name)
        return _json({"success": True, "switched_to": app_name})

    @mcp.tool()
    async def app_list_all() -> str:
        """List all available SciTeX apps.

        Returns app names, labels, icons, and ordering info.
        """
        from scitex_cloud.appmaker import list_all

        apps = list_all()
        return _json({"success": True, "count": len(apps), "apps": apps})

    @mcp.tool()
    async def app_get_info(app_name: str) -> str:
        """Get detailed info for a specific SciTeX app.

        Args:
            app_name: Name of the app (e.g. "writer", "scholar").
        """
        from scitex_cloud.appmaker import get_info

        info = get_info(app_name)
        if not info:
            return _json({"success": False, "error": f"App not found: {app_name}"})
        return _json({"success": True, "info": info})

    @mcp.tool()
    async def app_check_deps(app_dir: str = ".") -> str:
        """Check app dependencies from manifest.json.

        Reports which dependencies are missing (python, system, node, R).

        Args:
            app_dir: Path to the app directory containing manifest.json.
        """
        from pathlib import Path

        from scitex_cloud.appmaker import (
            check_deps_from_manifest,
            format_missing_report,
        )

        manifest = Path(app_dir) / "manifest.json"
        if not manifest.is_file():
            return _json({"success": False, "error": "No manifest.json found"})

        missing = check_deps_from_manifest(manifest)
        return _json(
            {
                "success": True,
                "all_satisfied": len(missing) == 0,
                "missing": missing,
                "report": format_missing_report(missing),
            }
        )

    @mcp.tool()
    async def app_get_prefs(app_name: str) -> str:
        """Get saved preferences for a SciTeX app.

        Args:
            app_name: Name of the app (e.g. "writer", "scholar").
        """
        from scitex_cloud.appmaker import get_prefs

        prefs = get_prefs(app_name)
        return _json({"success": True, "app": app_name, "prefs": prefs})

    @mcp.tool()
    async def app_set_prefs(app_name: str, prefs_json: str) -> str:
        """Set preferences for a SciTeX app. Merges with existing preferences.

        Args:
            app_name: Name of the app (e.g. "writer", "scholar").
            prefs_json: JSON string of key-value preferences to set.
        """
        import json

        from scitex_cloud.appmaker import set_prefs

        try:
            prefs = json.loads(prefs_json)
        except (json.JSONDecodeError, TypeError) as exc:
            return _json({"success": False, "error": f"Invalid JSON: {exc}"})

        if not isinstance(prefs, dict):
            return _json(
                {"success": False, "error": "prefs_json must be a JSON object"}
            )

        set_prefs(app_name, prefs)
        return _json({"success": True, "app": app_name, "saved": prefs})


# EOF
