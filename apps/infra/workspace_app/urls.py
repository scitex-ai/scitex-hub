#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django.urls import path

from . import views

app_name = "workspace_app"

urlpatterns = [
    # Workspace shell root (SPA default: writer)
    path("", views.workspace_shell, name="shell"),
    # AJAX content endpoint — must come before <str:module>/ catch-all
    path(
        "content/<str:module>/", views.workspace_module_content, name="module_content"
    ),
    # Legacy workspace container management — must come before <str:module>/ catch-all
    path("dashboard/", views.workspace_dashboard, name="dashboard"),
    path("start/", views.start_workspace, name="start"),
    path("stop/", views.stop_workspace, name="stop"),
    path("api/status/", views.workspace_status_api, name="status_api"),
    path("api/exec/", views.exec_command, name="exec"),
    # SPA module entry (e.g. /workspace/writer/, /workspace/scholar/)
    # Must be last to avoid shadowing the routes above
    path("<str:module>/", views.workspace_shell, name="shell_module"),
]

# EOF
