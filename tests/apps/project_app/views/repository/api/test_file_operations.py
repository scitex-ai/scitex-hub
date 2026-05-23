#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/project_app/views/repository/api/file_operations.py"""

import pytest

# from apps.infra.project_app.views.repository.api.file_operations import ...


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
# Start of Source Code from: apps/project_app/views/repository/api/file_operations.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-30 (auto-generated)"
# # File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/repository/api/file_operations.py
# # ----------------------------------------
# """
# File Operations API
#
# CRUD operations for files and directories within a project.
# Endpoints: create, delete, rename, copy
# """
#
# from __future__ import annotations
# import json
# import logging
# import shutil
# from pathlib import Path
#
# from django.shortcuts import get_object_or_404
# from django.contrib.auth.models import User
# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
#
# from ....models import Project
# from .permissions import check_project_write_access
#
# logger = logging.getLogger(__name__)
#
#
# def _get_project_path(project):
#     """Get the filesystem path for a project."""
#     from apps.infra.project_app.services.project_service_manager import ProjectServiceManager
#     service_manager = ProjectServiceManager(project)
#     return service_manager.get_project_path()
#
#
# def _validate_path(project_path, file_path):
#     """Validate that file_path is within project_path. Returns resolved path or None."""
#     try:
#         full_path = (project_path / file_path).resolve()
#         project_resolved = project_path.resolve()
#         if not str(full_path).startswith(str(project_resolved)):
#             return None
#         return full_path
#     except (ValueError, OSError, RuntimeError):
#         return None
#
#
# def _git_auto_commit(project, project_path, file_path, action):
#     """Auto-commit disabled - users should commit manually when ready.
#
#     This function is kept as a no-op for backward compatibility.
#     Git tracks changes but doesn't auto-commit, so git gutter shows modifications.
#     """
#     pass  # Auto-commit disabled
#
#
# @require_http_methods(["POST"])
# def api_file_create(request, username, slug):
#     """Create a new file or directory."""
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         data = json.loads(request.body)
#         file_path = data.get("path", "").strip()
#         item_type = data.get("type", "file")  # 'file' or 'directory'
#         content = data.get("content", "")
#
#         if not file_path:
#             return JsonResponse({"success": False, "error": "Path is required"}, status=400)
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         full_path = _validate_path(project_path, file_path)
#         if not full_path:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         if full_path.exists():
#             return JsonResponse({"success": False, "error": "File already exists"}, status=400)
#
#         # Create parent directories
#         full_path.parent.mkdir(parents=True, exist_ok=True)
#
#         if item_type == "directory":
#             full_path.mkdir(parents=True, exist_ok=True)
#         else:
#             full_path.write_text(content, encoding="utf-8")
#
#         _git_auto_commit(project, project_path, file_path, "Created")
#
#         return JsonResponse({
#             "success": True,
#             "message": f"{'Directory' if item_type == 'directory' else 'File'} created",
#             "path": file_path,
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.error(f"Error creating file: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_file_delete(request, username, slug):
#     """Delete a file or directory."""
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         data = json.loads(request.body)
#         file_path = data.get("path", "").strip()
#
#         if not file_path:
#             return JsonResponse({"success": False, "error": "Path is required"}, status=400)
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         full_path = _validate_path(project_path, file_path)
#         if not full_path:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         if not full_path.exists():
#             return JsonResponse({"success": False, "error": "File not found"}, status=404)
#
#         # Delete
#         if full_path.is_dir():
#             shutil.rmtree(full_path)
#         else:
#             full_path.unlink()
#
#         _git_auto_commit(project, project_path, file_path, "Deleted")
#
#         return JsonResponse({
#             "success": True,
#             "message": "Deleted successfully",
#             "path": file_path,
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.error(f"Error deleting file: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_file_rename(request, username, slug):
#     """Rename a file or directory."""
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         data = json.loads(request.body)
#         old_path = data.get("old_path", "").strip()
#         new_name = data.get("new_name", "").strip()
#
#         if not old_path or not new_name:
#             return JsonResponse({"success": False, "error": "old_path and new_name are required"}, status=400)
#
#         # Validate new_name (no path separators allowed)
#         if "/" in new_name or "\\" in new_name:
#             return JsonResponse({"success": False, "error": "new_name cannot contain path separators"}, status=400)
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         old_full_path = _validate_path(project_path, old_path)
#         if not old_full_path:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         if not old_full_path.exists():
#             return JsonResponse({"success": False, "error": "File not found"}, status=404)
#
#         # Calculate new path
#         new_full_path = old_full_path.parent / new_name
#         new_path = str(new_full_path.relative_to(project_path))
#
#         if new_full_path.exists():
#             return JsonResponse({"success": False, "error": "Target already exists"}, status=400)
#
#         # Rename
#         old_full_path.rename(new_full_path)
#
#         _git_auto_commit(project, project_path, new_path, "Renamed")
#
#         return JsonResponse({
#             "success": True,
#             "message": "Renamed successfully",
#             "old_path": old_path,
#             "new_path": new_path,
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.error(f"Error renaming file: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_file_copy(request, username, slug):
#     """Copy a file or directory."""
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         data = json.loads(request.body)
#         source_path = data.get("source_path", "").strip()
#         dest_path = data.get("dest_path", "").strip()
#
#         if not source_path or not dest_path:
#             return JsonResponse({"success": False, "error": "source_path and dest_path are required"}, status=400)
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         source_full = _validate_path(project_path, source_path)
#         dest_full = _validate_path(project_path, dest_path)
#
#         if not source_full or not dest_full:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         if not source_full.exists():
#             return JsonResponse({"success": False, "error": "Source not found"}, status=404)
#
#         if dest_full.exists():
#             return JsonResponse({"success": False, "error": "Destination already exists"}, status=400)
#
#         # Copy
#         dest_full.parent.mkdir(parents=True, exist_ok=True)
#         if source_full.is_dir():
#             shutil.copytree(source_full, dest_full)
#         else:
#             shutil.copy2(source_full, dest_full)
#
#         _git_auto_commit(project, project_path, dest_path, "Copied")
#
#         return JsonResponse({
#             "success": True,
#             "message": "Copied successfully",
#             "source_path": source_path,
#             "dest_path": dest_path,
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.error(f"Error copying file: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_file_move(request, username, slug):
#     """Move a file or directory to a new location.
#
#     For symlinks: recalculates the relative path to maintain the link target.
#     """
#     import os
#
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         data = json.loads(request.body)
#         source_path = data.get("source_path", "").strip()
#         dest_path = data.get("dest_path", "").strip()
#
#         if not source_path or not dest_path:
#             return JsonResponse({"success": False, "error": "source_path and dest_path are required"}, status=400)
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         source_full = _validate_path(project_path, source_path)
#         dest_full = _validate_path(project_path, dest_path)
#
#         if not source_full or not dest_full:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         if not source_full.exists() and not source_full.is_symlink():
#             return JsonResponse({"success": False, "error": "Source not found"}, status=404)
#
#         if dest_full.exists():
#             return JsonResponse({"success": False, "error": "Destination already exists"}, status=400)
#
#         # Prevent moving into itself
#         if str(dest_full).startswith(str(source_full) + "/"):
#             return JsonResponse({"success": False, "error": "Cannot move into itself"}, status=400)
#
#         # Handle symlinks specially - recalculate relative path
#         if source_full.is_symlink():
#             # Get the absolute target of the symlink
#             link_target = source_full.resolve()
#
#             # Create parent directories for destination
#             dest_full.parent.mkdir(parents=True, exist_ok=True)
#
#             # Calculate new relative path from destination to target
#             try:
#                 new_relative = os.path.relpath(link_target, dest_full.parent)
#             except ValueError:
#                 return JsonResponse(
#                     {"success": False, "error": "Cannot create relative path to symlink target"},
#                     status=400
#                 )
#
#             # Remove old symlink and create new one
#             source_full.unlink()
#             dest_full.symlink_to(new_relative)
#
#             logger.info(f"Moved symlink: {source_path} -> {dest_path} (target: {new_relative})")
#         else:
#             # Regular move for non-symlinks
#             dest_full.parent.mkdir(parents=True, exist_ok=True)
#             shutil.move(str(source_full), str(dest_full))
#
#         _git_auto_commit(project, project_path, dest_path, "Moved")
#
#         return JsonResponse({
#             "success": True,
#             "message": "Moved successfully",
#             "source_path": source_path,
#             "dest_path": dest_path,
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.error(f"Error moving file: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_file_upload(request, username, slug):
#     """Upload a file to the project."""
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         uploaded_file = request.FILES.get("file")
#         file_path = request.POST.get("path", "").strip()
#
#         if not uploaded_file:
#             return JsonResponse({"success": False, "error": "No file uploaded"}, status=400)
#
#         if not file_path:
#             file_path = uploaded_file.name
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         dest_full = _validate_path(project_path, file_path)
#         if not dest_full:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         # Create parent directories if needed
#         dest_full.parent.mkdir(parents=True, exist_ok=True)
#
#         # Write the file
#         with open(dest_full, "wb") as f:
#             for chunk in uploaded_file.chunks():
#                 f.write(chunk)
#
#         _git_auto_commit(project, project_path, file_path, "Uploaded")
#
#         return JsonResponse({
#             "success": True,
#             "message": "File uploaded successfully",
#             "path": file_path,
#             "size": uploaded_file.size,
#         })
#
#     except Exception as e:
#         logger.error(f"Error uploading file: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_file_upload_url(request, username, slug):
#     """Download a file from URL and save to project.
#
#     Useful for dragging images from web pages or Office products.
#     """
#     import requests
#     import mimetypes
#
#     try:
#         user = get_object_or_404(User, username=username)
#         project = get_object_or_404(Project, slug=slug, owner=user)
#
#         if not check_project_write_access(request, project):
#             return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
#
#         data = json.loads(request.body)
#         url = data.get("url", "").strip()
#         file_path = data.get("path", "").strip()
#
#         if not url:
#             return JsonResponse({"success": False, "error": "URL is required"}, status=400)
#
#         # Security: only allow http/https
#         if not url.startswith(('http://', 'https://')):
#             return JsonResponse({"success": False, "error": "Invalid URL scheme"}, status=400)
#
#         project_path = _get_project_path(project)
#         if not project_path or not project_path.exists():
#             return JsonResponse({"success": False, "error": "Project directory not found"}, status=404)
#
#         # Download the file
#         try:
#             resp = requests.get(url, timeout=30, stream=True, headers={
#                 'User-Agent': 'Mozilla/5.0 (compatible; SciTeX/1.0)'
#             })
#             resp.raise_for_status()
#         except requests.RequestException as e:
#             return JsonResponse({"success": False, "error": f"Failed to download: {str(e)}"}, status=400)
#
#         # Determine filename if not provided
#         if not file_path:
#             # Try to get from Content-Disposition header
#             cd = resp.headers.get('Content-Disposition', '')
#             if 'filename=' in cd:
#                 file_path = cd.split('filename=')[-1].strip('"\'')
#             else:
#                 # Extract from URL
#                 file_path = url.split('/')[-1].split('?')[0] or 'download'
#
#             # Add extension based on content type if missing
#             if '.' not in file_path:
#                 content_type = resp.headers.get('Content-Type', '').split(';')[0]
#                 ext = mimetypes.guess_extension(content_type) or '.bin'
#                 file_path += ext
#
#         dest_full = _validate_path(project_path, file_path)
#         if not dest_full:
#             return JsonResponse({"success": False, "error": "Invalid path"}, status=400)
#
#         # Create parent directories if needed
#         dest_full.parent.mkdir(parents=True, exist_ok=True)
#
#         # Write the file
#         with open(dest_full, "wb") as f:
#             for chunk in resp.iter_content(chunk_size=8192):
#                 f.write(chunk)
#
#         file_size = dest_full.stat().st_size
#         _git_auto_commit(project, project_path, file_path, "Downloaded")
#
#         return JsonResponse({
#             "success": True,
#             "message": "File downloaded successfully",
#             "path": file_path,
#             "size": file_size,
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.error(f"Error downloading file from URL: {e}", exc_info=True)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/project_app/views/repository/api/file_operations.py
# --------------------------------------------------------------------------------
