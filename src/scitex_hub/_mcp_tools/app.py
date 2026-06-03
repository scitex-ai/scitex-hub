#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/app.py
"""App management MCP tools — mirrors CLI commands for AI-driven app control."""

from __future__ import annotations

from .api import _json


def register_app_tools(mcp) -> None:
    """Register app management tools with FastMCP server."""

    @mcp.tool()
    async def app_get_current() -> str:
        """Use when the user asks which SciTeX app is active, wants to know the current context, or mentions app switching; replaces `scitex-hub app current` CLI invocations when the agent needs to introspect which app is selected (reads SCITEX_CURRENT_APP)."""
        from scitex_hub.appmaker import get_current

        name = get_current()
        return _json({"success": True, "current_app": name})

    @mcp.tool()
    async def app_switch_to(app_name: str) -> str:
        """Use when the user asks to switch apps, change to writer/scholar/etc., or mentions activating a different SciTeX app; replaces `scitex-hub app switch <name>` CLI invocations (sets SCITEX_CURRENT_APP).

        Args:
            app_name: Name of the app to switch to (e.g. "writer", "scholar").
        """
        from scitex_hub.appmaker import switch_to

        switch_to(app_name)
        return _json({"success": True, "switched_to": app_name})

    @mcp.tool()
    async def app_list_all() -> str:
        """Use when the user asks what SciTeX apps exist, to enumerate the app registry, or to pick an app; replaces `scitex-hub app list` CLI invocations when the agent needs to introspect available apps (names, labels, icons, ordering)."""
        from scitex_hub.appmaker import list_all

        apps = list_all()
        return _json({"success": True, "count": len(apps), "apps": apps})

    @mcp.tool()
    async def app_get_info(app_name: str) -> str:
        """Use when the user asks for details, metadata, or manifest of a specific SciTeX app; replaces `scitex-hub app info <name>` CLI invocations when the agent needs to introspect an app's config.

        Args:
            app_name: Name of the app (e.g. "writer", "scholar").
        """
        from scitex_hub.appmaker import get_info

        info = get_info(app_name)
        if not info:
            return _json({"success": False, "error": f"App not found: {app_name}"})
        return _json({"success": True, "info": info})

    @mcp.tool()
    async def app_check_deps(app_dir: str = ".") -> str:
        """Use when the user asks to verify an app's dependencies, check if python/node/system/R packages are installed, or diagnose a missing-dependency error for a SciTeX app; replaces `scitex-hub app check-deps` CLI invocations.

        Args:
            app_dir: Path to the app directory containing manifest.json.
        """
        from pathlib import Path

        from scitex_hub.appmaker import (
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
        """Use when the user asks for saved app settings, preferences, or config for a SciTeX app; replaces `scitex-hub app prefs get <name>` CLI invocations when the agent needs to introspect persisted user preferences.

        Args:
            app_name: Name of the app (e.g. "writer", "scholar").
        """
        from scitex_hub.appmaker import get_prefs

        prefs = get_prefs(app_name)
        return _json({"success": True, "app": app_name, "prefs": prefs})

    @mcp.tool()
    async def app_set_prefs(app_name: str, prefs_json: str) -> str:
        """Use when the user asks to save/update/merge preferences or settings for a SciTeX app; replaces `scitex-hub app prefs set <name> <json>` CLI invocations (merges with existing prefs; does not replace).

        Args:
            app_name: Name of the app (e.g. "writer", "scholar").
            prefs_json: JSON string of key-value preferences to set.
        """
        import json

        from scitex_hub.appmaker import set_prefs

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
