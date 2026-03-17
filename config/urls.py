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

from apps.infra.project_app.views import (
    accept_invitation,
    decline_invitation,
    project_create,
)
from apps.infra.public_app.views import healthz
from apps.workspace.hub_app.views.dispatch import root_dispatch
from apps.workspace.hub_app.views.index import current_project_view
from config.urls_helpers import RESERVED_PATHS, dev_module_view  # noqa: F401

urlpatterns = [
    # --- Health ---
    path("healthz/", healthz, name="healthz"),
    # --- Root ---
    path("", root_dispatch, name="root"),
    path("", include("apps.infra.public_app.urls")),
    path("apps/", include(("apps.workspace.tools_app.urls", "tools_app"))),
    # --- Admin ---
    path("admin/", admin.site.urls),
    # --- Auth ---
    path("accounts/", include(("apps.infra.accounts_app.urls", "accounts_app"))),
    path("auth/", include(("apps.infra.auth_app.urls", "auth_app"))),
    path("auth/social/", include("allauth.urls")),
    # --- Hub ---
    path("apps/home/api/", include("apps.workspace.hub_app.urls.api")),
    path("apps/home/", include("apps.workspace.hub_app.urls.index")),
    # --- Discovery ---
    path(
        "apps/discovery/",
        include(("apps.workspace.discovery_app.urls", "discovery_app")),
    ),
    # --- App modules (/apps/) ---
    path("apps/scholar/", include(("apps.workspace.scholar_app.urls", "scholar_app"))),
    path("apps/console/", include(("apps.workspace.console_app.urls", "console_app"))),
    path(
        "apps/figrecipe/",
        include(("apps.workspace.figrecipe_app.urls", "figrecipe_app")),
    ),
    path("apps/writer/", include(("apps.workspace.writer_app.urls", "writer_app"))),
    path(
        "apps/workspace/", include(("apps.infra.workspace_app.urls", "workspace_app"))
    ),
    path("apps/llm/", include(("apps.infra.llm_app.urls", "llm_app"))),
    path("apps/clew/", include(("apps.workspace.clew_app.urls", "clew_app"))),
    path("apps/store/", include(("apps.workspace.apps_app.urls", "apps_app"))),
    # --- Legacy redirects (/<app>/ → /apps/<app>/) ---
    path("", include("config.urls_legacy_redirects")),
    # --- Other apps ---
    path("dev/", include(("apps.workspace.dev_app.urls", "dev_app"))),
    path("apps/docs/", include(("apps.workspace.docs_app.urls", "docs_app"))),
    path(
        "integrations/",
        include(("apps.infra.integrations_app.urls", "integrations_app")),
    ),
    path(
        "organizations/",
        include(("apps.infra.organizations_app.urls", "organizations_app")),
    ),
    path("search/", include(("apps.infra.search_app.urls", "search_app"))),
    path("social/", include(("apps.infra.social_app.urls", "social_app"))),
    # --- API (/api/) ---
    path("api/", include("config.urls_api")),
    # --- Platform API ---
    path("platform/api/", include("apps.infra.platform_app.urls.api")),
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
        RedirectView.as_view(url="/apps/discovery/", permanent=True, query_string=True),
        name="hub_explore_redirect",
    ),
    path("current-project/", current_project_view, name="hub_current_project"),
    # --- GitHub-style catch-all (MUST BE LAST) ---
    path("<str:username>/", include(("apps.infra.project_app.urls", "user_projects"))),
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
