from django.urls import path
from .views import (
    profile_view,
    profile_edit,
    appearance_settings,
    account_settings,
    git_integrations,
    ssh_keys,
    remote_credentials,
    api_keys,
    api_generate_ssh_key,
)

app_name = "accounts_app"

urlpatterns = [
    # Profile views
    path("profile/", profile_view, name="profile"),
    path("settings/profile/", profile_edit, name="profile_edit"),
    path("settings/appearance/", appearance_settings, name="appearance"),
    path("settings/account/", account_settings, name="account"),
    # Integrations
    path("settings/integrations/", git_integrations, name="git_integrations"),
    # SSH Keys
    path("settings/ssh-keys/", ssh_keys, name="ssh_keys"),
    # Remote Credentials
    path("settings/remote/", remote_credentials, name="remote_credentials"),
    # API Keys
    path("settings/api-keys/", api_keys, name="api_keys"),
    # API Endpoints
    path(
        "api/ssh-keys/generate/",
        api_generate_ssh_key,
        name="api_generate_ssh_key",
    ),
]
