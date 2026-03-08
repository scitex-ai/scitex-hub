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
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView
from django.views.static import serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts_app.api.user_views import api_search_users
from apps.apps_app.views import api_registry_webhook, api_submit_jwt
from apps.hub_app.views.dispatch import root_dispatch
from apps.integrations_app.views_events import list_events, receive_event
from apps.project_app.views import (
    accept_invitation,
    api_check_name_availability,
    decline_invitation,
    project_create,
)
from apps.project_app.views.projects.api import (
    api_me,  # noqa: E402
    api_project_create_jwt,  # noqa: E402
    api_project_list_jwt,  # noqa: E402
    api_switch_active_project,  # noqa: E402
)
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
            "current-project",
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
    # Root: authenticated users → hub, visitors → /landing/
    path("", root_dispatch, name="root"),
    # Public pages (about, setup, contact, etc.) — all under their own prefixes
    path("", include("apps.public_app.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include(("apps.accounts_app.urls", "accounts_app"))),
    path("auth/", include(("apps.auth_app.urls", "auth_app"))),
    # Social authentication (Google, ORCID) via django-allauth
    path("auth/social/", include("allauth.urls")),
    # Main Modules
    # Hub workspace and API
    path("hub/api/", include("apps.hub_app.urls.api")),
    path("hub/", include("apps.hub_app.urls.index")),
    # Discovery app
    path("discovery/", include(("apps.discovery_app.urls", "discovery_app"))),
    # App modules — under /apps/ prefix (more-specific paths must come before apps/ catch-all)
    path("apps/scholar/", include(("apps.scholar_app.urls", "scholar_app"))),
    path("apps/console/", include(("apps.console_app.urls", "console_app"))),
    path("apps/vis-react/", include(("apps.vis_app.urls.vis_react", "vis_react"))),
    path("apps/vis/", include(("apps.vis_app.urls", "vis"))),
    path("apps/writer/", include(("apps.writer_app.urls", "writer_app"))),
    path("apps/workspace/", include(("apps.workspace_app.urls", "workspace_app"))),
    path("apps/example/", include(("apps.example_app.urls", "example_app"))),
    path("apps/notebook/", include(("apps.notebook_app.urls", "notebook_app"))),
    path(
        "apps/modulemaker/", include(("apps.modulemaker_app.urls", "modulemaker_app"))
    ),
    path("apps/llm/", include(("apps.llm_app.urls", "llm_app"))),
    path("apps/", include(("apps.apps_app.urls", "apps_app"))),
    # 301 redirects from legacy top-level paths → /apps/
    path(
        "scholar/",
        RedirectView.as_view(url="/apps/scholar/", permanent=True, query_string=True),
    ),
    path(
        "console/",
        RedirectView.as_view(url="/apps/console/", permanent=True, query_string=True),
    ),
    path(
        "vis/",
        RedirectView.as_view(url="/apps/vis/", permanent=True, query_string=True),
    ),
    path(
        "vis-react/",
        RedirectView.as_view(url="/apps/vis-react/", permanent=True, query_string=True),
    ),
    path(
        "writer/",
        RedirectView.as_view(url="/apps/writer/", permanent=True, query_string=True),
    ),
    path(
        "workspace/",
        RedirectView.as_view(url="/apps/workspace/", permanent=True, query_string=True),
    ),
    path(
        "example/",
        RedirectView.as_view(url="/apps/example/", permanent=True, query_string=True),
    ),
    path(
        "notebook/",
        RedirectView.as_view(url="/apps/notebook/", permanent=True, query_string=True),
    ),
    path(
        "modulemaker/",
        RedirectView.as_view(
            url="/apps/modulemaker/", permanent=True, query_string=True
        ),
    ),
    path(
        "llm/",
        RedirectView.as_view(url="/apps/llm/", permanent=True, query_string=True),
    ),
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
    # Platform services API (DataStore, FileVault, JobQueue, ExternalAPI, SciTeX bridge)
    path("platform/api/", include("apps.platform_app.urls.api")),
    # Shared workspace API (file content, etc.)
    path("api/workspace/", include("apps.workspace_api.urls")),
    # Event bus API (APIKey auth, CSRF exempt)
    path("api/events/", receive_event, name="event_receive"),
    path("api/events/list/", list_events, name="event_list"),
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
    # JWT-authenticated project APIs (for CLI access, no CSRF needed)
    path(
        "api/project/create/",
        csrf_exempt(api_project_create_jwt),
        name="api_project_create_jwt",
    ),
    path(
        "api/project/list/",
        csrf_exempt(api_project_list_jwt),
        name="api_project_list_jwt",
    ),
    path(
        "api/me/",
        csrf_exempt(api_me),
        name="api_me",
    ),
    # JWT-authenticated app submission + Gitea registry webhook
    path(
        "api/apps/submit/",
        csrf_exempt(api_submit_jwt),
        name="api_apps_submit_jwt",
    ),
    path(
        "api/apps/webhook/",
        csrf_exempt(api_registry_webhook),
        name="api_apps_registry_webhook",
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

# Clew verification (available in all environments)
urlpatterns += [
    path("apps/clew/", include(("apps.clew_app.urls", "clew"))),
    path(
        "clew/",
        RedirectView.as_view(url="/apps/clew/", permanent=True, query_string=True),
    ),
]

# Add development-only apps BEFORE catch-all username pattern
if settings.DEBUG:
    # Add django-browser-reload URLs for hot reload
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns += [
            path("__reload__/", include("django_browser_reload.urls")),
        ]

# Dev-installed app modules — serve via workspace shell (before <username> catch-all)
from apps.workspace_app.views import workspace_shell as _ws_shell


def _dev_module_view(request, rest):
    return _ws_shell(request, module=f"dev__{rest}")


urlpatterns += [
    path("dev__<str:rest>/", _dev_module_view, name="dev_module_shell"),
]

# Hub mode shortcuts — /current-project/ (before username catch-all)
from apps.hub_app.views.index import (  # noqa: E402
    current_project_view as _cp_view,
)

urlpatterns += [
    # /explore/ redirects to /discovery/ (discovery is now a standalone module)
    path(
        "explore/",
        RedirectView.as_view(url="/discovery/", permanent=True, query_string=True),
        name="hub_explore_redirect",
    ),
    path("current-project/", _cp_view, name="hub_current_project"),
]

# GitHub-style username/project URLs (MUST be last to avoid conflicts)
urlpatterns += [
    path("<str:username>/", include(("apps.project_app.urls", "user_projects"))),
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
