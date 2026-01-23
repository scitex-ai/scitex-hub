"""
Projects Feature URLs

Handles project CRUD operations and settings.
Patterns:
- /new/ - Create new project (handled in main config/urls.py)
- /<username>/<slug>/edit/ - Edit project
- /<username>/<slug>/delete/ - Delete project
- /<username>/<slug>/settings/ - Project settings
- /<username>/<slug>/settings/collaboration/ - Collaboration settings
- /<username>/<slug>/settings/members/ - Member management
- /<username>/<slug>/settings/integrations/ - Integration settings
"""

from django.urls import path
from ..views.projects import (
    project_edit,
    project_delete,
    project_create_from_template,
)
from ..views.settings_views import (
    project_settings,
)
from ..views.collaboration_views import (
    project_collaborate,
    project_members,
)
from ..views.integration_views import (
    github_integration,
)

# No app_name here - namespace is provided by parent (user_projects)

# Note: slug and username are passed via kwargs from parent URL pattern
urlpatterns = [
    # Project edit/delete
    path("edit/", project_edit, name="edit"),
    path("delete/", project_delete, name="delete"),
    path(
        "create-from-template/",
        project_create_from_template,
        name="create_from_template",
    ),
    # Settings URLs (GitHub-style /settings/ pattern)
    path("settings/", project_settings, name="settings"),
    path("settings/collaboration/", project_collaborate, name="collaborate"),
    path("settings/members/", project_members, name="members"),
    path("settings/integrations/", github_integration, name="github"),
]
