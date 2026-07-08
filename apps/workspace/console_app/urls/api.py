#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Console App API URLs

REST API endpoints for workspace and notebook operations:
- Workspace file operations (save, execute, command, create, delete)
- Git operations (status, diff, commit)
- File content redirect
- Jupyter Notebook API
"""

from django.urls import path
from django.views.generic import RedirectView

from .. import workspace_api as workspace_api_views
from ..views import api as api_views
from ..views.terminal.providers_api import api_terminal_providers

urlpatterns = [
    # Terminal model-provider picker (Option A model-agnostic sessions)
    path(
        "api/terminal/providers/",
        api_terminal_providers,
        name="api_terminal_providers",
    ),
    # Workspace API endpoints (file-content redirects to shared workspace_api app)
    path(
        "api/file-content/<path:file_path>",
        RedirectView.as_view(
            url="/api/workspace/file-content/%(file_path)s",
            query_string=True,
        ),
        name="api_file_content_redirect",
    ),
    path("api/save/", workspace_api_views.api_save_file, name="api_save_file"),
    path(
        "api/execute/",
        workspace_api_views.api_execute_script,
        name="api_execute_script",
    ),
    path(
        "api/command/",
        workspace_api_views.api_execute_command,
        name="api_execute_command",
    ),
    path(
        "api/create-file/", workspace_api_views.api_create_file, name="api_create_file"
    ),
    path("api/delete/", workspace_api_views.api_delete_file, name="api_delete_file"),
    # Git status and diff endpoints
    path(
        "api/git-status/", workspace_api_views.api_get_git_status, name="api_git_status"
    ),
    path(
        "api/file-diff/<path:file_path>",
        workspace_api_views.api_get_file_diff,
        name="api_file_diff",
    ),
    path("api/git-commit/", workspace_api_views.api_git_commit, name="api_git_commit"),
    # Jupyter Notebook API endpoints
    path("api/notebooks/", api_views.NotebookListAPI.as_view(), name="api_notebooks"),
    path(
        "api/notebooks/<uuid:notebook_id>/",
        api_views.NotebookDetailAPI.as_view(),
        name="api_notebook_detail",
    ),
    path(
        "api/notebooks/<uuid:notebook_id>/execute/",
        api_views.NotebookExecutionAPI.as_view(),
        name="api_notebook_execute",
    ),
    path(
        "api/notebooks/<uuid:notebook_id>/convert/<str:format_type>/",
        api_views.NotebookConversionAPI.as_view(),
        name="api_notebook_convert",
    ),
    path(
        "api/notebooks/<uuid:notebook_id>/share/",
        api_views.NotebookSharingAPI.as_view(),
        name="api_notebook_share",
    ),
    path(
        "api/notebooks/<uuid:notebook_id>/duplicate/",
        api_views.duplicate_notebook_api,
        name="api_notebook_duplicate",
    ),
    path(
        "api/templates/",
        api_views.NotebookTemplatesAPI.as_view(),
        name="api_notebook_templates",
    ),
    path(
        "api/jobs/<uuid:job_id>/status/",
        api_views.notebook_status_api,
        name="api_job_status",
    ),
]

# EOF
