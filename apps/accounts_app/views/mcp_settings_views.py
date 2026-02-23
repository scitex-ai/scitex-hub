"""MCP Tools settings page — toggle MCP tool groups for Claude Code in Apptainer."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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
        "desc": "23 statistical tests with effect sizes",
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


def _build_groups_context(prefs: dict) -> list[dict]:
    """Build template context for MCP tool groups with current toggle states."""
    groups = []
    for name in DEFAULT_MCP_GROUPS:
        info = MCP_GROUP_INFO.get(
            name, {"display": name, "icon": "fa-puzzle-piece", "desc": ""}
        )
        # Default: all enabled
        enabled = prefs.get(name, True)
        groups.append(
            {
                "name": name,
                "display": info["display"],
                "icon": info["icon"],
                "desc": info["desc"],
                "enabled": enabled,
            }
        )
    return groups


def _regenerate_claude_config(user):
    """Regenerate .claude/settings.json with updated MCP preferences."""
    from apps.console_app.services.agents_config import ensure_claude_config
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

    return ensure_claude_config(user_data_dir, mcp_env=mcp_env, force=True)


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

    groups = _build_groups_context(prefs)
    return render(request, "accounts_app/mcp_settings.html", {"groups": groups})
