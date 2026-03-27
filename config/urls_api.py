# -*- coding: utf-8 -*-
# Timestamp: 2026-03-09
# File: /home/ywatanabe/proj/scitex-cloud/config/urls_api.py
"""
Consolidated top-level API routes (/api/...).
Extracted from config/urls.py for clarity.
"""

from __future__ import annotations

from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.infra.accounts_app.api.user_views import api_search_users
from apps.infra.integrations_app.views_events import list_events, receive_event
from apps.infra.project_app.views import api_check_name_availability
from apps.infra.project_app.views.projects.api import (
    api_me,
    api_project_create_jwt,
    api_project_list_jwt,
    api_switch_active_project,
)
from apps.workspace.apps_app.views import api_registry_webhook, api_submit_jwt

urlpatterns = [
    # JWT Token endpoints (for programmatic API access)
    path(
        "token/",
        csrf_exempt(TokenObtainPairView.as_view()),
        name="token_obtain_pair",
    ),
    path(
        "token/refresh/",
        csrf_exempt(TokenRefreshView.as_view()),
        name="token_refresh",
    ),
    # User info
    path("me/", csrf_exempt(api_me), name="api_me"),
    # Project management
    path(
        "project/create/",
        csrf_exempt(api_project_create_jwt),
        name="api_project_create_jwt",
    ),
    path(
        "project/list/",
        csrf_exempt(api_project_list_jwt),
        name="api_project_list_jwt",
    ),
    path(
        "project/switch/",
        api_switch_active_project,
        name="api_switch_active_project",
    ),
    path(
        "project/check-name/",
        api_check_name_availability,
        name="api_check_name",
    ),
    # App submission + Gitea registry webhook
    path(
        "apps/submit/",
        csrf_exempt(api_submit_jwt),
        name="api_apps_submit_jwt",
    ),
    path(
        "apps/webhook/",
        csrf_exempt(api_registry_webhook),
        name="api_apps_registry_webhook",
    ),
    # Gitea → Django org/member sync webhook
    path(
        "gitea/webhook/sync/",
        __import__(
            "apps.infra.gitea_app.views.webhook_sync", fromlist=["gitea_sync_webhook"]
        ).gitea_sync_webhook,
        name="api_gitea_sync_webhook",
    ),
    # Event bus
    path("events/", receive_event, name="event_receive"),
    path("events/list/", list_events, name="event_list"),
    # User search
    path("users/search/", api_search_users, name="api_search_users"),
    # Shared workspace API
    path("workspace/", include("apps.infra.workspace_api.urls")),
    # Public Scholar API (v1)
    path("v1/scholar/", include("apps.workspace.scholar_app.urls.public_api")),
    # MCP Tools REST API (auto-generated from MCP tool registry)
    path("v1/tools/", include("apps.infra.mcp_api.urls")),
]

# EOF
