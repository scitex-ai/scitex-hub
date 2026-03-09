# -*- coding: utf-8 -*-
# scitex-linter: skip-file
# Timestamp: 2026-03-09
# File: /home/ywatanabe/proj/scitex-cloud/config/urls.py
"""
URL Configuration for SciTeX Cloud project.
Organized into clear sections; helpers, API routes, and legacy redirects
are extracted into separate modules.
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from apps.hub_app.views.dispatch import root_dispatch
from apps.hub_app.views.index import current_project_view
from apps.project_app.views import accept_invitation, decline_invitation, project_create
from apps.public_app.views import healthz
from config.urls_helpers import RESERVED_PATHS, dev_module_view  # noqa: F401

urlpatterns = [
    # --- Health ---
    path("healthz/", healthz, name="healthz"),
    # --- Root ---
    path("", root_dispatch, name="root"),
    path("", include("apps.public_app.urls")),
    # --- Admin ---
    path("admin/", admin.site.urls),
    # --- Auth ---
    path("accounts/", include(("apps.accounts_app.urls", "accounts_app"))),
    path("auth/", include(("apps.auth_app.urls", "auth_app"))),
    path("auth/social/", include("allauth.urls")),
    # --- Hub ---
    path("hub/api/", include("apps.hub_app.urls.api")),
    path("hub/", include("apps.hub_app.urls.index")),
    # --- Discovery ---
    path("discovery/", include(("apps.discovery_app.urls", "discovery_app"))),
    # --- App modules (/apps/) ---
    path("apps/scholar/", include(("apps.scholar_app.urls", "scholar_app"))),
    path("apps/console/", include(("apps.console_app.urls", "console_app"))),
    path("apps/vis-react/", include(("apps.vis_app.urls.vis_react", "vis_react"))),
    path("apps/vis/", include(("apps.vis_app.urls", "vis"))),
    path("apps/writer/", include(("apps.writer_app.urls", "writer_app"))),
    path("apps/workspace/", include(("apps.workspace_app.urls", "workspace_app"))),
    path("apps/example/", include(("apps.example_app.urls", "example_app"))),
    path("apps/notebook/", include(("apps.notebook_app.urls", "notebook_app"))),
    path("apps/appmaker/", include(("apps.appmaker_app.urls", "appmaker_app"))),
    path("apps/llm/", include(("apps.llm_app.urls", "llm_app"))),
    path("apps/clew/", include(("apps.clew_app.urls", "clew"))),
    path("apps/", include(("apps.apps_app.urls", "apps_app"))),
    # --- Legacy redirects (/<app>/ → /apps/<app>/) ---
    path("", include("config.urls_legacy_redirects")),
    # --- Other apps ---
    path("dev/", include(("apps.dev_app.urls", "dev_app"))),
    path("docs/", include(("apps.docs_app.urls", "docs_app"))),
    path("integrations/", include(("apps.integrations_app.urls", "integrations_app"))),
    path(
        "organizations/", include(("apps.organizations_app.urls", "organizations_app"))
    ),
    path("search/", include(("apps.search_app.urls", "search_app"))),
    path("social/", include(("apps.social_app.urls", "social_app"))),
    # --- API (/api/) ---
    path("api/", include("config.urls_api")),
    # --- Platform API ---
    path("platform/api/", include("apps.platform_app.urls.api")),
    # --- Legacy: /project/api/check-name/ → now at /api/project/check-name/ ---
    path(
        "project/api/check-name/",
        RedirectView.as_view(url="/api/project/check-name/", permanent=True),
    ),
    # --- Favicon ---
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/shared/images/favicon.png", permanent=True),
    ),
    # --- GitHub-like operations ---
    path("new/", project_create, name="project_create"),
    path(
        "invitations/<str:token>/accept/", accept_invitation, name="accept_invitation"
    ),
    path(
        "invitations/<str:token>/decline/",
        decline_invitation,
        name="decline_invitation",
    ),
    # --- Dev module shell ---
    path("dev__<str:rest>/", dev_module_view, name="dev_module_shell"),
    # --- Hub shortcuts ---
    path(
        "explore/",
        RedirectView.as_view(url="/discovery/", permanent=True, query_string=True),
        name="hub_explore_redirect",
    ),
    path("current-project/", current_project_view, name="hub_current_project"),
    # --- GitHub-style catch-all (MUST BE LAST) ---
    path("<str:username>/", include(("apps.project_app.urls", "user_projects"))),
]

# --- Debug-only ---
if settings.DEBUG:
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns.insert(
            -1,
            path("__reload__/", include("django_browser_reload.urls")),
        )
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# --- Production media fallback ---
if not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

# EOF
