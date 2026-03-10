#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discovery App URL configuration."""

from django.urls import path

from apps.infra.workspace_app.views import workspace_shell

from . import views

app_name = "discovery_app"

urlpatterns = [
    path("", workspace_shell, {"module": "discovery"}, name="index"),
    path("api/explore/", views.api_explore, name="api_explore"),
]

# EOF
