"""Customize hub — AI agent configuration dispatcher."""

from django.shortcuts import render


def customize_hub(request):
    """Hub page showing cards for AI agent configuration categories."""
    categories = [
        {
            "name": "MCP Servers",
            "description": "Configure Model Context Protocol servers and their tools",
            "icon": "fas fa-plug",
            "url": "/accounts/settings/mcp-tools/",
            "count_label": "servers",
        },
        {
            "name": "AI Providers",
            "description": "API keys and model preferences for AI backends",
            "icon": "fas fa-brain",
            "url": "/accounts/settings/ai-providers/",
            "count_label": "providers",
        },
        {
            "name": "Appearance",
            "description": "Theme, layout, and display preferences",
            "icon": "fas fa-palette",
            "url": "/accounts/settings/appearance/",
            "count_label": None,
        },
        {
            "name": "Profile",
            "description": "Your account profile and preferences",
            "icon": "fas fa-user-cog",
            "url": "/accounts/settings/profile/",
            "count_label": None,
        },
        {
            "name": "Integrations",
            "description": "Git, SSH keys, and external service connections",
            "icon": "fas fa-link",
            "url": "/accounts/settings/integrations/",
            "count_label": None,
        },
        {
            "name": "API Keys",
            "description": "Manage API access tokens for programmatic use",
            "icon": "fas fa-key",
            "url": "/accounts/settings/api-keys/",
            "count_label": None,
        },
    ]

    return render(
        request,
        "accounts_app/customize_hub.html",
        {"categories": categories},
    )
