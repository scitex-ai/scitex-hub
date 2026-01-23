"""
Users Feature URLs

Handles user profile and user-level operations.
GitHub-style patterns:
- /<username>/ - User profile/overview
- /<username>?tab=repositories - User's projects
- /<username>?tab=stars - User's starred projects
- /<username>/settings/repositories/ - Repository maintenance
"""

from django.urls import path
from ..views.users import (
    user_profile,
)
from ..views.integration_views import (
    repository_maintenance,
)
from ..views.api_views import (
    api_repository_health,
    api_repository_cleanup,
    api_repository_sync,
    api_repository_restore,
)

# No app_name here - namespace is provided by parent (user_projects)

# Note: username is passed via kwargs from parent URL pattern
urlpatterns = [
    # User profile - GitHub-style /<username>/ with ?tab support
    path("", user_profile, name="profile"),
    # Repository maintenance dashboard
    path(
        "settings/repositories/", repository_maintenance, name="repository_maintenance"
    ),
    # Repository maintenance and health check APIs
    path("api/repository-health/", api_repository_health, name="api_repository_health"),
    path(
        "api/repository-cleanup/", api_repository_cleanup, name="api_repository_cleanup"
    ),
    path("api/repository-sync/", api_repository_sync, name="api_repository_sync"),
    path(
        "api/repository-restore/", api_repository_restore, name="api_repository_restore"
    ),
]
