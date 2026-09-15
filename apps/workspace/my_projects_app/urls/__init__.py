#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub app URLs package."""

from django.urls import include, path

app_name = "my_projects_app"

urlpatterns = [
    # API endpoints (must be first to match /api/* routes)
    path("api/", include("apps.workspace.my_projects_app.urls.api")),
    # Main index (must be last as catch-all)
    path("", include("apps.workspace.my_projects_app.urls.index")),
]
