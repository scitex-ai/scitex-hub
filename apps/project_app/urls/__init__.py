"""
Project App URL Configuration

Feature-based URL organization following FULLSTACK.md guidelines.

This module assembles URLs from all feature modules:
- repository: File browsing, commits, directory navigation
- pull_requests: PR creation, review, merge
- issues: Issue tracking, labels, milestones
- security: Security alerts, scans, advisories
- workflows: CI/CD workflows (pending implementation)
- projects: Project CRUD and settings
- users: User profiles and maintenance
- actions: Social interactions (watch, star, fork)

URL Structure (GitHub-style):
    /<username>/                           - User profile
    /<username>/<slug>/                    - Repository root
    /<username>/<slug>/pulls/              - Pull requests
    /<username>/<slug>/issues/             - Issues
    /<username>/<slug>/security/           - Security
    /<username>/<slug>/actions/            - Workflows (pending)
    /<username>/<slug>/settings/           - Project settings
    /<username>/<slug>/blob/<path>         - File view
    /<username>/<slug>/commit/<hash>/      - Commit detail

Note: This replaces the old user_urls.py and urls.py files.
The main config/urls.py includes this at: path('<str:username>/', include('apps.project_app.urls'))
"""

from django.urls import path, include
from .. import views
from ..api_views_module import api_views
from ..views import security_views
from ..views import pr as pr_views

app_name = "user_projects"


# Wrapper view to pass username from URL kwargs to the view
def user_profile_wrapper(request, username):
    return views.user_profile(request, username)


def repository_maintenance_wrapper(request, username):
    return views.repository_maintenance(request, username)


# Project-level wrapper to include slug
def project_wrapper_with_feature(feature_urls):
    """
    Helper to create URL patterns that include slug parameter
    before routing to feature modules.
    """
    return feature_urls


urlpatterns = [
    # User-level URLs (no slug required)
    # /<username>/ - Profile/Overview (with ?tab= query params)
    path("", user_profile_wrapper, name="user_profile"),
    # Repository maintenance dashboard
    path(
        "settings/repositories/",
        repository_maintenance_wrapper,
        name="repository_maintenance",
    ),
    # Repository maintenance and health check APIs
    path(
        "api/repository-health/",
        views.api_repository_health,
        name="api_repository_health",
    ),
    path(
        "api/repository-cleanup/",
        views.api_repository_cleanup,
        name="api_repository_cleanup",
    ),
    path("api/repository-sync/", views.api_repository_sync, name="api_repository_sync"),
    path(
        "api/repository-restore/",
        views.api_repository_restore,
        name="api_repository_restore",
    ),
    # Project-level URLs (require slug parameter)
    # /<username>/<slug>/...
    # Pull Requests feature - /pulls/ prefix
    path("<slug:slug>/pulls/", include("apps.project_app.urls.pull_requests")),
    # Pull Request compare (separate from /pulls/ - GitHub pattern)
    path("<slug:slug>/pull/new/", pr_views.pr_create, name="pr_create"),
    path("<slug:slug>/pull/<int:pr_number>/", pr_views.pr_detail, name="pr_detail"),
    path("<slug:slug>/compare/<str:compare>/", pr_views.pr_compare, name="pr_compare"),
    # Pull Request API endpoints
    path("<slug:slug>/pull/<int:pr_number>/merge/", pr_views.pr_merge, name="pr_merge"),
    path("<slug:slug>/pull/<int:pr_number>/close/", pr_views.pr_close, name="pr_close"),
    path(
        "<slug:slug>/pull/<int:pr_number>/reopen/", pr_views.pr_reopen, name="pr_reopen"
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/review/",
        pr_views.pr_review_submit,
        name="pr_review_submit",
    ),
    path(
        "<slug:slug>/pull/<int:pr_number>/comment/",
        pr_views.pr_comment_create,
        name="pr_comment_create",
    ),
    # Issues feature
    path("<slug:slug>/issues/", include("apps.project_app.urls.issues")),
    # Security feature
    path("<slug:slug>/security/", include("apps.project_app.urls.security")),
    # Workflows feature (placeholder for now)
    # path('<slug:slug>/actions/', include('apps.project_app.urls.workflows')),
    # Project management (settings, edit, delete)
    path("<slug:slug>/", include("apps.project_app.urls.projects")),
    # Social actions (watch, star, fork)
    path("<slug:slug>/api/", include("apps.project_app.urls.actions")),
    # Repository browsing (must be last as it has catch-all patterns)
    path("<slug:slug>/", include("apps.project_app.urls.repository")),
]
