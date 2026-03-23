"""AI Setup hub — AI agent configuration dispatcher."""

import logging
import time

from django.shortcuts import render

logger = logging.getLogger(__name__)

# Simple in-memory cache: {key: (timestamp, data)}
_cache: dict[str, tuple[float, list]] = {}
_CACHE_TTL = 300  # 5 minutes


def _cached(key: str, fetcher, ttl: int = _CACHE_TTL) -> list:
    """Cache wrapper for slow data fetchers."""
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < ttl:
            return data
    try:
        data = fetcher()
        _cache[key] = (now, data)
        return data
    except Exception as e:
        logger.warning("Cache fetch failed for %s: %s", key, e)
        # Return stale data if available
        if key in _cache:
            return _cache[key][1]
        return []


def customize_hub(request):
    """Hub page showing cards for AI agent configuration categories."""
    categories = [
        {
            "name": "Skills",
            "description": "Specialized capabilities that guide AI behavior",
            "icon": "fas fa-graduation-cap",
            "url": "/customize/skills/",
        },
        {
            "name": "Commands",
            "description": "Slash commands that trigger predefined workflows",
            "icon": "fas fa-terminal",
            "url": "/customize/commands/",
        },
        {
            "name": "Hooks",
            "description": "Automated actions triggered by events",
            "icon": "fas fa-bolt",
            "url": "/customize/hooks/",
        },
        {
            "name": "MCP Servers",
            "description": "Model Context Protocol servers and tools",
            "icon": "fas fa-plug",
            "url": "/customize/mcp-servers/",
        },
        {
            "name": "CLI Commands",
            "description": "Command-line tools in the terminal environment",
            "icon": "fas fa-code",
            "url": "/customize/cli-commands/",
        },
        {
            "name": "AI Providers",
            "description": "API keys and model preferences for AI backends",
            "icon": "fas fa-brain",
            "url": "/accounts/settings/ai-providers/",
        },
    ]

    if request.headers.get("X-Workspace-Shell") == "1":
        template = "accounts_app/customize_hub_partial.html"
    else:
        template = "accounts_app/customize_hub.html"

    return render(request, template, {"categories": categories})


# Valid section names and their display info
_SECTIONS = {
    "skills": {"title": "Skills", "icon": "fas fa-graduation-cap"},
    "commands": {"title": "Commands", "icon": "fas fa-terminal"},
    "hooks": {"title": "Hooks", "icon": "fas fa-bolt"},
    "mcp-servers": {"title": "MCP Servers", "icon": "fas fa-plug"},
    "cli-commands": {"title": "CLI Commands", "icon": "fas fa-code"},
}


def customize_section(request, section):
    """Render a customize sub-section (skills, commands, etc.)."""
    from django.http import Http404

    info = _SECTIONS.get(section)
    if not info:
        raise Http404(f"Unknown customize section: {section}")

    ctx = {
        "section": section,
        "section_title": info["title"],
        "section_icon": info["icon"],
        "items": _get_section_items(section, user=request.user),
    }

    if request.headers.get("X-Workspace-Shell") == "1":
        template = "accounts_app/customize_section_partial.html"
    else:
        template = "accounts_app/customize_section.html"

    return render(request, template, ctx)


def customize_mcp_server(request, server):
    """Show individual MCP server tools with per-tool toggle."""
    from apps.infra.accounts_app.views.mcp_settings_views import (
        MCP_GROUP_INFO,
        _get_tool_info,
    )

    group_key = server.upper()
    info = MCP_GROUP_INFO.get(group_key)
    if not info:
        from django.http import Http404

        raise Http404(f"Unknown MCP server: {server}")

    _, tool_names = _get_tool_info()
    tools = tool_names.get(group_key, [])

    ctx = {
        "section": "mcp-servers",
        "section_title": info["display"],
        "section_icon": f"fas {info['icon']}",
        "server_key": group_key,
        "server_desc": info["desc"],
        "items": [
            {
                "name": name,
                "description": name.replace("_", " ").title(),
                "icon": f"fas {info['icon']}",
                "has_toggle": True,
                "enabled": True,
            }
            for name in tools
        ],
        "back_url": "/customize/mcp-servers/",
    }

    if request.headers.get("X-Workspace-Shell") == "1":
        template = "accounts_app/customize_section_partial.html"
    else:
        template = "accounts_app/customize_section.html"

    return render(request, template, ctx)


def _get_section_items(section, user=None):
    """Fetch items for a customize section (with caching for slow calls)."""
    if section == "skills":
        return _cached("skills", _get_skills)
    if section == "mcp-servers":
        return _get_mcp_servers(user=user)
    if section == "cli-commands":
        return _cached("cli-commands", _get_cli_commands)
    if section == "commands":
        return _cached("commands", _get_commands)
    if section == "hooks":
        return _cached("hooks", _get_hooks)
    return []


def _get_skills():
    """Get skills from scitex skills list CLI."""
    import logging
    import re
    import subprocess

    logger = logging.getLogger(__name__)
    try:
        result = subprocess.run(
            ["python", "-m", "scitex", "skills", "list"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("scitex skills list failed: %s", result.stderr[:200])
        items = []
        current_pkg = ""
        skill_name = "SKILL"
        for line in result.stdout.splitlines():
            if line.startswith("WARN:") or not line.strip():
                continue
            # Package header (no leading whitespace, ends with ':')
            if not line.startswith(" ") and line.endswith(":"):
                current_pkg = line.rstrip(":")
                skill_name = "SKILL"
                continue
            # Skill entry (2-space indent, name on its own line)
            m = re.match(r"^  (\S+)$", line)
            if m:
                skill_name = m.group(1)
                continue
            # Description (4-space indent)
            m = re.match(r"^    (.+)$", line)
            if m and current_pkg:
                name = (
                    current_pkg
                    if skill_name == "SKILL"
                    else f"{current_pkg}:{skill_name}"
                )
                items.append(
                    {
                        "name": name,
                        "description": m.group(1)[:120],
                        "icon": "fas fa-graduation-cap",
                    }
                )
        return items
    except Exception:
        return []


def _get_mcp_servers(user=None):
    """Get MCP tool groups with toggle state and tool counts."""
    try:
        from apps.infra.accounts_app.views.mcp_settings_views import (
            MCP_GROUP_INFO,
            _get_tool_info,
        )
        from apps.workspace.console_app.services.agents_config import DEFAULT_MCP_GROUPS

        counts, _ = _get_tool_info()

        # Get user preferences
        prefs = {}
        if user and user.is_authenticated:
            profile = getattr(user, "profile", None)
            if profile:
                prefs = getattr(profile, "mcp_preferences", None) or {}

        items = []
        for key, info in MCP_GROUP_INFO.items():
            count = counts.get(key, 0)
            enabled = prefs.get(key, key in DEFAULT_MCP_GROUPS)
            items.append(
                {
                    "name": info["display"],
                    "key": key.lower(),
                    "group_key": key,
                    "description": info["desc"],
                    "icon": f"fas {info['icon']}",
                    "count": count,
                    "enabled": enabled,
                    "url": f"/customize/mcp-servers/{key.lower()}/",
                    "has_toggle": True,
                }
            )
        return items
    except Exception:
        return []


def _get_cli_commands():
    """Get CLI commands from scitex --help-recursive."""
    try:
        import subprocess

        result = subprocess.run(
            ["python", "-m", "scitex", "--help-recursive"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        items = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("Usage") and not line.startswith("Options"):
                if line.startswith("scitex "):
                    cmd = line.split()[1] if len(line.split()) > 1 else line
                    items.append(
                        {"name": cmd, "description": line, "icon": "fas fa-code"}
                    )
        return items[:50]
    except Exception:
        return []


def _get_commands():
    """Get slash commands from .claude/commands/."""
    import pathlib

    items = []
    for d in [pathlib.Path.home() / ".claude" / "commands"]:
        if d.is_dir():
            for f in sorted(d.glob("*.md")):
                items.append(
                    {
                        "name": f"/{f.stem}",
                        "description": f.stem.replace("-", " ").title(),
                        "icon": "fas fa-terminal",
                    }
                )
    return items


def _get_hooks():
    """Get hooks from .claude/hooks/."""
    import pathlib

    items = []
    for d in [pathlib.Path.home() / ".claude" / "hooks"]:
        if d.is_dir():
            for sub in sorted(d.iterdir()):
                if sub.is_dir():
                    for f in sorted(sub.glob("*")):
                        if f.is_file() and not f.name.startswith("."):
                            items.append(
                                {
                                    "name": f"{sub.name}/{f.name}",
                                    "description": sub.name,
                                    "icon": "fas fa-bolt",
                                }
                            )
    return items
