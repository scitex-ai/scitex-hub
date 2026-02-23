"""Account app views - modularized for maintainability."""

# Profile views
# AI providers views
from .ai_providers_views import ai_providers

# API keys views
from .api_keys_views import api_keys

# MCP settings views
from .mcp_settings_views import mcp_settings
from .profile_views import (
    appearance_settings,
    profile_edit,
    profile_view,
)

# Remote credentials views
from .remote_credentials_views import remote_credentials

# Settings and integrations views
from .settings_views import (
    account_settings,
    git_integrations,
    repository_health,
)

# SSH key views
from .ssh_views import (
    api_generate_ssh_key,
    ssh_keys,
)

__all__ = [
    # Profile views
    "profile_view",
    "profile_edit",
    "appearance_settings",
    # SSH key views
    "ssh_keys",
    "api_generate_ssh_key",
    # Remote credentials views
    "remote_credentials",
    # API keys views
    "api_keys",
    # Settings and integrations views
    "account_settings",
    "git_integrations",
    "repository_health",
    # AI providers views
    "ai_providers",
    # MCP settings views
    "mcp_settings",
]
