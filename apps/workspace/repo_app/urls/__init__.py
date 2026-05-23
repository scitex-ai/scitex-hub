#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub app URLs package."""

from django.urls import include, path

app_name = "repo_app"

urlpatterns = [
    # API endpoints (must be first to match /api/* routes)
    path("api/", include("apps.workspace.repo_app.urls.api")),
    # Main index (must be last as catch-all)
    path("", include("apps.workspace.repo_app.urls.index")),
]
