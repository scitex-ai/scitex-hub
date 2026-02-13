# -*- coding: utf-8 -*-
# scitex-linter: skip-file
# Timestamp: "2025-11-04 20:27:37 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/config/urls.py
# ----------------------------------------
"""
URL Configuration for SciTeX Cloud project.
Django URL configuration modules are not scripts.
"""

from __future__ import annotations

# ----------------------------------------

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import re_path
from django.views.static import serve
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts_app.api.user_views import api_search_users
from apps.project_app.views import (
    accept_invitation,
    api_check_name_availability,
    decline_invitation,
    project_create,
)
from apps.project_app.views.projects.api import api_switch_active_project
from apps.public_app.views import healthz


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
            "healthz",
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
    # Critical health check endpoint (must come before username catch-all)
    path("healthz/", healthz, name="healthz"),
    # Basics
    path("", include("apps.public_app.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include(("apps.accounts_app.urls", "accounts_app"))),
    path("auth/", include(("apps.auth_app.urls", "auth_app"))),
    # Social authentication (Google, ORCID) via django-allauth
    path("auth/social/", include("allauth.urls")),
    # Main Modules
    path("hub/", include(("apps.hub_app.urls", "hub_app"))),
    path("scholar/", include(("apps.scholar_app.urls", "scholar_app"))),
    path("console/", include(("apps.console_app.urls", "console_app"))),
    path("vis/", include(("apps.vis_app.urls", "vis"))),
    path("writer/", include(("apps.writer_app.urls", "writer_app"))),
    path("workspace/", include(("apps.workspace_app.urls", "workspace_app"))),
    # LLM/Agent Support
    path("llm/", include(("apps.llm_app.urls", "llm_app"))),
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
    path(
        "api/project/switch/",
        api_switch_active_project,
        name="api_switch_active_project",
    ),
    # Citation Graph API now under scholar/ namespace (removed from here)
    # Public Scholar API (v1) - accessible without scholar/ prefix
    path(
        "api/v1/scholar/",
        include("apps.scholar_app.urls.public_api"),
    ),
    # JWT Token endpoints (for programmatic API access) - CSRF exempt for curl/API clients
    path(
        "api/token/",
        csrf_exempt(TokenObtainPairView.as_view()),
        name="token_obtain_pair",
    ),
    path(
        "api/token/refresh/",
        csrf_exempt(TokenRefreshView.as_view()),
        name="token_refresh",
    ),
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

# Add development-only apps BEFORE catch-all username pattern
if settings.DEBUG:
    urlpatterns += [
        path("clew/", include(("apps.clew_app.urls", "clew"))),
    ]
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


# Serve static and media files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Always serve media files via Django fallback (nginx serves in prod,
# but staging/dev need Django to handle media when nginx is absent)
if not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

# EOF
