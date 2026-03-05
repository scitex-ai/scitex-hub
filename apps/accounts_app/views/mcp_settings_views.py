"""MCP Tools settings page — toggle MCP tool groups for Claude Code in Apptainer."""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.console_app.services.agents_config import DEFAULT_MCP_GROUPS

logger = logging.getLogger(__name__)

# Display metadata for each MCP tool group
MCP_GROUP_INFO = {
    "PLT": {
        "display": "Plotting",
        "icon": "fa-chart-line",
        "desc": "Create publication-ready figures",
    },
    "STATS": {
        "display": "Statistics",
        "icon": "fa-calculator",
        "desc": "Statistical tests with effect sizes",
    },
    "SCHOLAR": {
        "display": "Literature",
        "icon": "fa-book",
        "desc": "Search papers, manage citations",
    },
    "WRITER": {
        "display": "Manuscript",
        "icon": "fa-pen-fancy",
        "desc": "LaTeX writing, PDF compilation",
    },
    "CLEW": {
        "display": "Pipelines",
        "icon": "fa-project-diagram",
        "desc": "CLEW pipeline execution",
    },
    "AUDIO": {
        "display": "Speech",
        "icon": "fa-volume-up",
        "desc": "Text-to-speech in browser",
    },
    "DIAGRAM": {
        "display": "Diagrams",
        "icon": "fa-sitemap",
        "desc": "Mermaid, Graphviz diagrams",
    },
    "CAPTURE": {
        "display": "Screenshots",
        "icon": "fa-camera",
        "desc": "Capture screenshots",
    },
    "INTROSPECT": {
        "display": "API Inspector",
        "icon": "fa-search-plus",
        "desc": "Explore scitex API",
    },
    "TEMPLATE": {
        "display": "Templates",
        "icon": "fa-copy",
        "desc": "Project templates",
    },
    "PROJECT": {
        "display": "File Management",
        "icon": "fa-folder-open",
        "desc": "Read/write project files",
    },
    "DATASET": {
        "display": "Datasets",
        "icon": "fa-database",
        "desc": "Access research datasets",
    },
    "DEV": {"display": "Developer", "icon": "fa-code", "desc": "Development tools"},
    "LINTER": {
        "display": "Code Quality",
        "icon": "fa-check-circle",
        "desc": "Linting and code checks",
    },
    "SOCIAL": {
        "display": "Social",
        "icon": "fa-share-alt",
        "desc": "Social media posting",
    },
    "UI": {
        "display": "Notifications",
        "icon": "fa-bell",
        "desc": "Browser notifications",
    },
    "USAGE": {
        "display": "Usage",
        "icon": "fa-tachometer-alt",
        "desc": "Usage tracking",
    },
}

# Logical categories for organized display
MCP_CATEGORIES = [
    ("Research & Analysis", ["PLT", "STATS", "DATASET"]),
    ("Writing & Publishing", ["SCHOLAR", "WRITER", "DIAGRAM"]),
    ("Development", ["DEV", "LINTER", "INTROSPECT", "TEMPLATE", "PROJECT"]),
    ("Automation", ["CLEW", "CAPTURE", "AUDIO", "UI", "SOCIAL"]),
    ("System", ["USAGE"]),
]


def _get_tool_info() -> tuple[dict, list]:
    """Get tool counts per group and tool names. Returns (counts, tool_names_by_group)."""
    try:
        from scitex.mcp_server import FASTMCP_AVAILABLE
        from scitex.mcp_server import mcp as mcp_server

        if not FASTMCP_AVAILABLE or mcp_server is None:
            return {}, {}

        # FastMCP 2.x/3.x compat
        tm = getattr(mcp_server, "_tool_manager", None)
        if tm is not None and hasattr(tm, "_tools"):
            tools = dict(tm._tools)
        else:
            return {}, {}

        counts = {}
        names = {}
        for name in sorted(tools.keys()):
            prefix = name.split("_")[0].upper()
            counts[prefix] = counts.get(prefix, 0) + 1
            names.setdefault(prefix, []).append(name)
        return counts, names
    except Exception:
        return {}, {}


def _get_mcp_status() -> dict:
    """Get MCP server health status."""
    try:
        from scitex.mcp_server import FASTMCP_AVAILABLE
        from scitex.mcp_server import mcp as mcp_server

        if not FASTMCP_AVAILABLE:
            return {"status": "unavailable", "message": "FastMCP not installed"}
        if mcp_server is None:
            return {"status": "unavailable", "message": "MCP server not initialized"}

        tm = getattr(mcp_server, "_tool_manager", None)
        if tm is not None and hasattr(tm, "_tools"):
            count = len(tm._tools)
            return {
                "status": "healthy",
                "message": f"{count} tools loaded",
                "count": count,
            }
        return {"status": "warning", "message": "Tool manager unavailable"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _build_categories_context(prefs: dict) -> list[dict]:
    """Build template context grouped by category with tool counts."""
    tool_counts, tool_names = _get_tool_info()
    categories = []
    for cat_name, group_keys in MCP_CATEGORIES:
        groups = []
        for name in group_keys:
            if name not in DEFAULT_MCP_GROUPS:
                continue
            info = MCP_GROUP_INFO.get(
                name, {"display": name, "icon": "fa-puzzle-piece", "desc": ""}
            )
            enabled = prefs.get(name, True)
            groups.append(
                {
                    "name": name,
                    "display": info["display"],
                    "icon": info["icon"],
                    "desc": info["desc"],
                    "enabled": enabled,
                    "tool_count": tool_counts.get(name, 0),
                    "tools": tool_names.get(name, []),
                }
            )
        if groups:
            categories.append({"name": cat_name, "groups": groups})
    return categories


def _regenerate_claude_config(user):
    """Regenerate .mcp.json and .agents/agents.json with updated MCP preferences."""
    from apps.console_app.services.agents_config import (
        ensure_agents_config,
        ensure_claude_config,
    )
    from apps.console_app.views.terminal.config import USER_DATA_ROOT

    username = user.username
    user_data_dir = USER_DATA_ROOT / username
    if not user_data_dir.exists():
        return False

    prefs = getattr(user.profile, "mcp_preferences", {}) or {}
    mcp_env = {}
    for group in DEFAULT_MCP_GROUPS:
        if prefs.get(group, True):
            mcp_env[f"SCITEX_MCP_USE_{group}"] = "1"

    proj_dir = user_data_dir / "proj"
    regenerated = False
    if proj_dir.exists():
        for project_dir in proj_dir.iterdir():
            if project_dir.is_dir() and project_dir.name != "dotfiles":
                ensure_agents_config(project_dir, mcp_env=mcp_env, force=True)
                ensure_claude_config(
                    user_data_dir, project_dir, mcp_env=mcp_env, force=True
                )
                regenerated = True
    return regenerated


@login_required
def mcp_settings(request):
    """MCP Tools settings page."""
    profile = request.user.profile
    prefs = profile.mcp_preferences or {}

    if request.method == "POST":
        new_prefs = {}
        for name in DEFAULT_MCP_GROUPS:
            new_prefs[name] = request.POST.get(f"mcp_{name}") == "on"

        profile.mcp_preferences = new_prefs
        profile.save(update_fields=["mcp_preferences"])

        regenerated = _regenerate_claude_config(request.user)
        if regenerated:
            messages.success(
                request,
                "MCP tool preferences saved. Changes apply next time you start Claude Code.",
            )
        else:
            messages.success(request, "MCP tool preferences saved.")

        return redirect("accounts_app:mcp_tools")

    categories = _build_categories_context(prefs)
    mcp_status = _get_mcp_status()
    return render(
        request,
        "accounts_app/mcp_settings.html",
        {"categories": categories, "mcp_status": mcp_status},
    )


@login_required
@require_http_methods(["GET", "POST"])
def mcp_settings_api(request):
    """AJAX endpoint for reading/saving MCP tool preferences."""
    if request.method == "GET":
        prefs = request.user.profile.mcp_preferences or {}
        categories = _build_categories_context(prefs)
        mcp_status = _get_mcp_status()
        return JsonResponse({"categories": categories, "status": mcp_status})

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    new_prefs = {}
    for name in DEFAULT_MCP_GROUPS:
        new_prefs[name] = bool(data.get(name, True))

    profile = request.user.profile
    profile.mcp_preferences = new_prefs
    profile.save(update_fields=["mcp_preferences"])

    regenerated = _regenerate_claude_config(request.user)
    return JsonResponse({"ok": True, "regenerated": regenerated})


# Default auto-response values (must match auto-response-config.ts DEFAULT_CONFIG)
AUTO_RESPONSE_DEFAULTS = {
    "y_n": "1",
    "y_y_n": "2",
    "waiting": "/speak-signature",
    "suggestion": "",
}

# Allowed keys for auto-response preferences
AUTO_RESPONSE_KEYS = frozenset(AUTO_RESPONSE_DEFAULTS.keys())


@login_required
@require_http_methods(["GET", "POST"])
def auto_response_prefs_api(request):
    """AJAX endpoint for reading/saving auto-response command preferences."""
    profile = request.user.profile
    prefs = profile.auto_response_preferences or {}

    if request.method == "GET":
        # Merge defaults with saved prefs
        merged = {**AUTO_RESPONSE_DEFAULTS, **prefs}
        return JsonResponse({"responses": merged})

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Only accept known keys, coerce to string
    new_prefs = {}
    for key in AUTO_RESPONSE_KEYS:
        if key in data:
            new_prefs[key] = str(data[key])

    profile.auto_response_preferences = new_prefs
    profile.save(update_fields=["auto_response_preferences"])
    return JsonResponse({"ok": True, "responses": new_prefs})
