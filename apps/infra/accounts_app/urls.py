from django.urls import path
from django.views.generic import RedirectView

from .views import (
    account_settings,
    ai_limits_api,
    ai_providers,
    api_generate_ssh_key,
    api_keys,
    appearance_settings,
    auto_response_prefs_api,
    git_integrations,
    mcp_settings,
    mcp_settings_api,
    profile_edit,
    profile_view,
    remote_credentials,
    repository_health,
    ssh_keys,
)

app_name = "accounts_app"

urlpatterns = [
    # Settings root redirect
    path(
        "settings/",
        RedirectView.as_view(pattern_name="accounts_app:profile_edit"),
        name="settings",
    ),
    # Profile views
    path("profile/", profile_view, name="profile"),
    path("settings/profile/", profile_edit, name="profile_edit"),
    path("settings/appearance/", appearance_settings, name="appearance"),
    path("settings/account/", account_settings, name="account"),
    # Integrations
    path("settings/integrations/", git_integrations, name="git_integrations"),
    path("settings/ai-providers/", ai_providers, name="ai_providers"),
    path("settings/mcp-tools/", mcp_settings, name="mcp_tools"),
    # SSH Keys
    path("settings/ssh-keys/", ssh_keys, name="ssh_keys"),
    # Remote Credentials
    path("settings/remote/", remote_credentials, name="remote_credentials"),
    # API Keys
    path("settings/api-keys/", api_keys, name="api_keys"),
    # Repositories
    path("settings/repository-health/", repository_health, name="repository_health"),
    # API Endpoints
    path(
        "api/ssh-keys/generate/",
        api_generate_ssh_key,
        name="api_generate_ssh_key",
    ),
    path(
        "api/mcp-preferences/",
        mcp_settings_api,
        name="mcp_settings_api",
    ),
    path(
        "api/ai-limits/",
        ai_limits_api,
        name="ai_limits_api",
    ),
    path(
        "api/auto-response-prefs/",
        auto_response_prefs_api,
        name="auto_response_prefs_api",
    ),
]
