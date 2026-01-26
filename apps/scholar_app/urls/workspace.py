#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs - Workspace and API key management page endpoints."""

from __future__ import annotations

from django.urls import path

from ..views.workspace import api_key_views
from ..views.workspace import views as workspace_views

# Workspace pages
urlpatterns = [
    # Default workspace for logged-in users without project
    path(
        "workspace/",
        workspace_views.user_default_workspace,
        name="user_default_workspace",
    ),
    # API Key Management page and endpoints
    path("api-keys/", api_key_views.api_key_management, name="api_keys"),
    path("api/test-api-key/", api_key_views.test_api_key, name="test_api_key"),
    path("api/usage-stats/", api_key_views.api_usage_stats, name="api_usage_stats"),
]


# EOF
