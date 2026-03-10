#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/workspace_api/file_create_delete.py"""

import pytest

# from apps.workspace.console_app.workspace_api.file_create_delete import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/console_app/workspace_api/file_create_delete.py
# --------------------------------------------------------------------------------
# """
# Code Workspace API Views - File operations for the simple editor.
# """
#
# import json
# import logging
# import subprocess
# from pathlib import Path
#
# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
# from django.contrib.auth.decorators import login_required
# from apps.infra.project_app.models import Project
# from apps.infra.project_app.services.git_status import get_git_status, get_file_diff
# from apps.infra.project_app.services.git_service import git_commit_and_push
#
# logger = logging.getLogger(__name__)
#
#
# @require_http_methods(["GET"])
# def api_create_file(request):
#     """Create a new file (supports both local and remote projects)."""
#     try:
#         data = json.loads(request.body)
#         project_id = data.get("project_id")
#         file_path = data.get("path")
#         content = data.get("content", "")
#
#         if not project_id or not file_path:
#             return JsonResponse({"error": "Missing required fields"}, status=400)
#
#         project = Project.objects.select_related("owner").get(id=project_id)
#
#         # Check permissions (allow authenticated users and visitors with allocated project)
#         if request.user.is_authenticated:
#             has_access = (
#                 request.user == project.owner
#                 or request.user in project.collaborators.all()
#             )
#         else:
#             # For visitor users, check if this is their allocated visitor project
#             visitor_project_id = request.session.get("visitor_project_id")
#             has_access = (visitor_project_id and project.id == visitor_project_id)
#
#         if not has_access:
#             return JsonResponse({"error": "Unauthorized"}, status=403)
#
#         # Get project path (works for both local and remote projects)
#         from apps.infra.project_app.services.project_service_manager import ProjectServiceManager
#         service_manager = ProjectServiceManager(project)
#         project_path = service_manager.get_project_path()
#
#         file_full_path = project_path / file_path
#
#         # Security check
#         if not str(file_full_path.resolve()).startswith(
#             str(project_path.resolve())
#         ):
#             return JsonResponse({"error": "Invalid file path"}, status=400)
#
#         # Check if file already exists
#         if file_full_path.exists():
#             return JsonResponse({"error": "File already exists"}, status=400)
#
#         # Create parent directories if needed
#         file_full_path.parent.mkdir(parents=True, exist_ok=True)
#
#         # Create file
#         with open(file_full_path, "w", encoding="utf-8") as f:
#             f.write(content)
#
#         # Auto-commit disabled - users should commit manually when ready
#         # New files will show as "untracked" in git gutter
#
#         return JsonResponse({
#             "success": True,
#             "message": "File created successfully",
#             "path": file_path,
#             "project_type": project.project_type,
#         })
#
#     except Exception as e:
#         logger.error(f"Error creating file: {e}", exc_info=True)
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_delete_file(request):
#     """Delete a file or folder (supports both local and remote projects)."""
#     try:
#         data = json.loads(request.body)
#         project_id = data.get("project_id")
#         file_path = data.get("path")
#
#         if not project_id or not file_path:
#             return JsonResponse({"error": "Missing required fields"}, status=400)
#
#         project = Project.objects.select_related("owner").get(id=project_id)
#
#         # Check permissions (allow authenticated users and visitors with allocated project)
#         if request.user.is_authenticated:
#             has_access = (
#                 request.user == project.owner
#                 or request.user in project.collaborators.all()
#             )
#         else:
#             # For visitor users, check if this is their allocated visitor project
#             visitor_project_id = request.session.get("visitor_project_id")
#             has_access = (visitor_project_id and project.id == visitor_project_id)
#
#         if not has_access:
#             return JsonResponse({"error": "Unauthorized"}, status=403)
#
#         # Get project path (works for both local and remote projects)
#         from apps.infra.project_app.services.project_service_manager import ProjectServiceManager
#         service_manager = ProjectServiceManager(project)
#         project_path = service_manager.get_project_path()
#
#         file_full_path = project_path / file_path
#
#         # Security check
#         if not str(file_full_path.resolve()).startswith(
#             str(project_path.resolve())
#         ):
#             return JsonResponse({"error": "Invalid file path"}, status=400)
#
#         if not file_full_path.exists():
#             return JsonResponse({"error": "File/folder not found"}, status=404)
#
#         # Delete file or folder
#         import shutil
#         if file_full_path.is_dir():
#             shutil.rmtree(file_full_path)
#         else:
#             file_full_path.unlink()
#
#         # Auto-commit disabled - users should commit manually when ready
#         # Deleted files will show with strike-through in git gutter until committed
#
#         return JsonResponse({
#             "success": True,
#             "message": "Deleted successfully",
#             "path": file_path,
#             "project_type": project.project_type,
#         })
#
#     except Exception as e:
#         logger.error(f"Error deleting: {e}", exc_info=True)
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/console_app/workspace_api/file_create_delete.py
# --------------------------------------------------------------------------------
