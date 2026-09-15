#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public Projects App URL configuration."""

from django.urls import path

from . import views

app_name = "public_projects_app"

urlpatterns = [
    # One pane (no legacy three-pane shell with its chat + file panes).
    path("", views.public_projects_index, name="index"),
    path("api/explore/", views.api_explore, name="api_explore"),
]

# EOF
