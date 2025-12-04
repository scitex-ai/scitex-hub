#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 20:27:37 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/config/urls.py
# ----------------------------------------
from __future__ import annotations
import os
__FILE__ = (
    "./config/urls.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
URL Configuration for SciTeX Cloud project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views.generic import RedirectView
from apps.accounts_app.api.user_views import api_search_users
from apps.project_app.views import project_create
from apps.project_app.views import api_check_name_availability
from apps.project_app.views import accept_invitation
from apps.project_app.views import decline_invitation
from apps.project_app.views.projects.api import api_switch_active_project


# Functions
def get_reserved_paths():
    """
    Dynamically generate list of reserved URL prefixes.
    Returns list of paths that cannot be used as usernames.
    """
    from pathlib import Path

    reserved = set()

    # 1. Auto-discover app URL prefixes
    apps_dir = Path(settings.BASE_DIR) / "apps"
    if apps_dir.exists():
        for app_dir in sorted(apps_dir.iterdir()):
            if app_dir.is_dir() and not app_dir.name.startswith("_"):
                urls_file = app_dir / "urls.py"
                if urls_file.exists():
                    # Extract URL prefix (remove _app suffix)
                    url_prefix = app_dir.name.replace("_app", "")
                    reserved.add(url_prefix)

    # 2. Static system paths
    reserved.update(
        [
            "admin",
            "api",
            "new",
            "static",
            "media",
            "accounts",
            "auth",
            "files",
            "favicon.ico",
            "robots.txt",
            "sitemap.xml",
        ]
    )

    # 3. Common reserved words (user-facing pages)
    reserved.update(
        [
            "about",
            "help",
            "support",
            "contact",
            "terms",
            "privacy",
            "settings",
            "dashboard",
            "profile",
            "account",
            "login",
            "logout",
            "signup",
            "register",
            "reset",
            "verify",
            "confirm",
            "explore",
            "trending",
            "discover",
            "social",  # Social auth URLs
        ]
    )

    # 4. Development/debug paths
    if settings.DEBUG:
        reserved.update(["__reload__", "__debug__"])

    return sorted(list(reserved))


# Generate reserved paths dynamically
RESERVED_PATHS = get_reserved_paths()

# Build URL patterns with correct ordering
urlpatterns = [
    # Basics
    path("", include("apps.public_app.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include(("apps.accounts_app.urls", "accounts_app"))),
    path("auth/", include(("apps.auth_app.urls", "auth_app"))),
    # Social authentication (Google, ORCID) via django-allauth
    path("auth/social/", include("allauth.urls")),
    # Main Modules
    path("scholar/", include(("apps.scholar_app.urls", "scholar_app"))),
    path("code/", include(("apps.code_app.urls", "code_app"))),
    path("vis/", include(("apps.vis_app.urls", "vis"))),
    path("writer/", include(("apps.writer_app.urls", "writer_app"))),
    path("workspace/", include(("apps.workspace_app.urls", "workspace_app"))),
    # Deveopment
    path("dev/", include(("apps.dev_app.urls", "dev_app"))),
    path("docs/", include(("apps.docs_app.urls", "docs_app"))),
    # Etc.
    path("donations/", include(("apps.donations_app.urls", "donations_app"))),
    path(
        "integrations/",
        include(("apps.integrations_app.urls", "integrations_app")),
    ),
    path(
        "organizations/",
        include(("apps.organizations_app.urls", "organizations_app")),
    ),
    path("search/", include(("apps.search_app.urls", "search_app"))),
    path("social/", include(("apps.social_app.urls", "social_app"))),
    # Favicon redirect to prevent 404 errors
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/shared/images/favicon.png", permanent=True),
    ),
    # API endpoints
    path("api/users/search/", api_search_users, name="api_search_users"),
    path("project/api/check-name/", api_check_name_availability, name="api_check_name"),
    path("api/project/switch/", api_switch_active_project, name="api_switch_active_project"),
    # GitHub-like operations
    # /new - Create new project
    path("new/", project_create, name="project_create"),
    # Invitation accept/decline
    path(
        "invitations/<str:token>/accept/",
        accept_invitation,
        name="accept_invitation",
    ),
    path(
        "invitations/<str:token>/decline/",
        decline_invitation,
        name="decline_invitation",
    ),
]

# Add development tools BEFORE catch-all username pattern
if settings.DEBUG:
    # Add django-browser-reload URLs for hot reload
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns += [
            path("__reload__/", include("django_browser_reload.urls")),
        ]

# Explicit /files/ prefix for development clarity (redundant with /<username>/)
urlpatterns += [
    path("files/<str:username>/", include("apps.project_app.urls")),
]

# GitHub-style username/project URLs (MUST be last to avoid conflicts)
urlpatterns += [
    path("<str:username>/", include("apps.project_app.urls")),
]

# Custom error handlers (imported from apps)
from apps.public_app.error_views import handler404


# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

# EOF
