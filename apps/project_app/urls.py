from django.urls import path
from . import views

app_name = "project_app"

urlpatterns = [
    # Legacy routes for backward compatibility - redirect to user_projects namespace
    # These are accessed via /project/ prefix (configured in config/urls.py)
    path("", views.project_list, name="list"),
    # GitHub-style project creation at /project/new/
    path("new/", views.project_create, name="create"),
    # API endpoints (keep numeric IDs for API)
    path("api/check-name/", views.api_check_name_availability, name="api_check_name"),
    path("api/list/", views.api_project_list, name="api_list"),
    path("api/create/", views.api_project_create, name="api_create"),
    path("api/<int:pk>/", views.api_project_detail, name="api_detail"),
    # GitHub-style project URLs (/<username>/<slug>/)
    # Repository API endpoints
    path("<slug:slug>/api/file-tree/", views.api_file_tree, name="api_file_tree"),
    path("<slug:slug>/api/create-symlink/", views.api_create_symlink, name="api_create_symlink"),
    path("<slug:slug>/api/concatenate-directory/", views.api_concatenate_directory, name="api_concatenate_directory"),
    path("<slug:slug>/api/repository-health/", views.api_repository_health, name="api_repository_health"),
    path("<slug:slug>/api/repository-cleanup/", views.api_repository_cleanup, name="api_repository_cleanup"),
    path("<slug:slug>/api/repository-sync/", views.api_repository_sync, name="api_repository_sync"),
    path("<slug:slug>/api/repository-restore/", views.api_repository_restore, name="api_repository_restore"),
    # Backward compatibility redirects
    path("project/<slug:slug>/", views.project_detail_redirect, name="slug_redirect"),
    path("id/<int:pk>/", views.project_detail_redirect, name="detail_redirect"),
]
