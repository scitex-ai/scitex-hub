"""Customize hub — AI agent configuration dispatcher."""

from django.shortcuts import render


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
        "items": _get_section_items(section),
    }

    if request.headers.get("X-Workspace-Shell") == "1":
        template = "accounts_app/customize_section_partial.html"
    else:
        template = "accounts_app/customize_section.html"

    return render(request, template, ctx)


def _get_section_items(section):
    """Fetch items for a customize section."""
    if section == "skills":
        return _get_skills()
    if section == "mcp-servers":
        return _get_mcp_servers()
    # Placeholder for other sections
    return []


def _get_skills():
    """Get registered skills."""
    try:
        from apps.infra.llm_app.skills import get_all_skills

        skills = get_all_skills()
        return [
            {
                "name": s.display_name or name,
                "key": name,
                "description": s.description or "",
                "icon": "fas fa-graduation-cap",
            }
            for name, s in skills.items()
        ]
    except Exception:
        return []


def _get_mcp_servers():
    """Get MCP server tools from preferences."""
    try:
        from apps.infra.accounts_app.views.mcp_settings_views import (
            MCP_TOOL_GROUPS,
        )

        return [
            {
                "name": g["label"],
                "key": g["key"],
                "description": f"{g['count']} tools",
                "icon": "fas fa-plug",
            }
            for g in MCP_TOOL_GROUPS
        ]
    except Exception:
        return []
