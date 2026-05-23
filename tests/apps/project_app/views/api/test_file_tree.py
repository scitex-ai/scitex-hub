#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/project_app/views/api/file_tree.py"""

import pytest

# from apps.infra.project_app.views.api.file_tree import ...


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
# Start of Source Code from: apps/project_app/views/api/file_tree.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-29 (auto-generated)"
# # File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/api/file_tree.py
# # ----------------------------------------
# """
# File Tree API Views
#
# This module contains API endpoints for project file tree navigation.
# """
#
# from __future__ import annotations
# import logging
#
# from django.shortcuts import get_object_or_404
# from django.contrib.auth.models import User
# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
#
# from ...models import Project
# from ...services.git_status import get_git_status
#
# logger = logging.getLogger(__name__)
#
#
# # ============================================================================
# # File Tree API
# # ============================================================================
#
#
# @require_http_methods(["GET"])
# def api_file_tree(request, username, slug):
#     """API endpoint to get project file tree for sidebar navigation"""
#     user = get_object_or_404(User, username=username)
#     project = get_object_or_404(Project, slug=slug, owner=user)
#
#     # Check access (allow public access for public projects)
#     if request.user.is_authenticated:
#         has_access = (
#             project.owner == request.user
#             or project.collaborators.filter(id=request.user.id).exists()
#             or project.visibility == "public"
#         )
#     else:
#         # For visitor users, check if this is their allocated visitor project
#         visitor_project_id = request.session.get("visitor_project_id")
#         has_access = (
#             project.visibility == "public"
#             or (visitor_project_id and project.id == visitor_project_id)
#         )
#
#     if not has_access:
#         return JsonResponse({"success": False, "error": "Permission denied"})
#
#     # Get project directory
#     from apps.infra.project_app.services.project_filesystem import (
#         get_project_filesystem_manager,
#     )
#
#     manager = get_project_filesystem_manager(project.owner)
#     project_path = manager.get_project_root_path(project)
#
#     if not project_path or not project_path.exists():
#         return JsonResponse({"success": False, "error": "Project directory not found"})
#
#     # Get git status for all files in the project
#     git_statuses_raw = get_git_status(project_path)
#     # Normalize paths: remove trailing slashes for consistent matching
#     git_statuses = {k.rstrip('/'): v for k, v in git_statuses_raw.items()}
#
#     # Track untracked directories - these need to propagate status to children
#     # When git reports "?? some/dir/" it means entire directory is untracked
#     untracked_dirs = set()
#     for file_path, status_obj in git_statuses.items():
#         if status_obj.status == '??':
#             # Check if this is a directory (ends with / in raw status or exists as dir)
#             untracked_dirs.add(file_path)
#
#     # Build a set of directory paths that contain modified files
#     # This allows us to propagate git status up to parent directories
#     dirs_with_changes = {}  # path -> aggregated status
#     for file_path, status_obj in git_statuses.items():
#         # Add status to all parent directories
#         parts = file_path.split('/')
#         for i in range(len(parts) - 1):  # Exclude the file itself
#             dir_path = '/'.join(parts[:i + 1])
#             if dir_path not in dirs_with_changes:
#                 # Use 'M' (modified) as default for directories with changes
#                 dirs_with_changes[dir_path] = {
#                     "status": "M",
#                     "staged": status_obj.staged,
#                 }
#             elif status_obj.staged:
#                 # If any child is staged, mark directory as having staged changes
#                 dirs_with_changes[dir_path]["staged"] = True
#
#     def get_inherited_untracked_status(rel_path_str):
#         """Check if this path is inside an untracked directory"""
#         for untracked_dir in untracked_dirs:
#             if rel_path_str.startswith(untracked_dir + '/') or rel_path_str == untracked_dir:
#                 return {"status": "??", "staged": False}
#         return None
#
#     def build_tree(path, max_depth=10, current_depth=0):
#         """Build file tree recursively (deeper for full navigation)"""
#         items = []
#         try:
#             for item in sorted(
#                 path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
#             ):
#                 # Skip hidden files except .git directory, .gitignore, and .gitkeep
#                 if item.name.startswith(".") and item.name not in [
#                     ".git",
#                     ".gitignore",
#                     ".gitkeep",
#                 ]:
#                     continue
#                 # Skip common non-essential directories
#                 if item.name in [
#                     "__pycache__",
#                     "node_modules",
#                     ".venv",
#                     "venv",
#                 ]:
#                     continue
#
#                 rel_path = item.relative_to(project_path)
#                 rel_path_str = str(rel_path)
#
#                 # Check git status for this file/directory
#                 git_status = None
#                 if rel_path_str in git_statuses:
#                     # Direct file status
#                     status_obj = git_statuses[rel_path_str]
#                     git_status = {
#                         "status": status_obj.status,
#                         "staged": status_obj.staged,
#                     }
#                 elif item.is_dir() and rel_path_str in dirs_with_changes:
#                     # Directory has children with changes
#                     git_status = dirs_with_changes[rel_path_str]
#                 else:
#                     # Check if this item is inside an untracked directory
#                     git_status = get_inherited_untracked_status(rel_path_str)
#
#                 item_data = {
#                     "name": item.name,
#                     "type": "directory" if item.is_dir() else "file",
#                     "path": rel_path_str,
#                     "git_status": git_status,
#                 }
#
#                 # Add children for directories (deeper depth for full tree)
#                 if item.is_dir() and current_depth < max_depth:
#                     item_data["children"] = build_tree(
#                         item, max_depth, current_depth + 1
#                     )
#
#                 items.append(item_data)
#         except PermissionError:
#             pass
#
#         return items
#
#     tree = build_tree(project_path)
#
#     # Add deleted files (exist in git but deleted from filesystem) to the tree
#     # These show with strike-through in the UI
#     deleted_files = [
#         (path, status) for path, status in git_statuses.items()
#         if status.status == 'D'
#     ]
#
#     def add_deleted_to_tree(tree_items, deleted_path, git_status, parent_path=""):
#         """Recursively add a deleted file to the correct location in the tree."""
#         parts = deleted_path.split('/')
#         if len(parts) == 1:
#             # This is the file itself, add it to current level
#             file_name = parts[0]
#             # Check if it already exists (shouldn't, but be safe)
#             if not any(item['name'] == file_name for item in tree_items):
#                 tree_items.append({
#                     "name": file_name,
#                     "type": "file",
#                     "path": deleted_path,
#                     "git_status": {"status": git_status.status, "staged": git_status.staged},
#                     "deleted": True,  # Mark as deleted for UI handling
#                 })
#                 # Re-sort: directories first, then by name
#                 tree_items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
#         else:
#             # Need to navigate/create directories
#             dir_name = parts[0]
#             remaining_path = '/'.join(parts[1:])
#             current_path = f"{parent_path}/{dir_name}" if parent_path else dir_name
#
#             # Find or create the directory
#             dir_item = None
#             for item in tree_items:
#                 if item['name'] == dir_name and item['type'] == 'directory':
#                     dir_item = item
#                     break
#
#             if dir_item is None:
#                 # Create the directory (it might have been deleted too)
#                 dir_item = {
#                     "name": dir_name,
#                     "type": "directory",
#                     "path": current_path,
#                     "git_status": {"status": "D", "staged": git_status.staged},
#                     "children": [],
#                 }
#                 tree_items.append(dir_item)
#                 tree_items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
#
#             if 'children' not in dir_item:
#                 dir_item['children'] = []
#
#             add_deleted_to_tree(dir_item['children'], remaining_path, git_status, current_path)
#
#     for deleted_path, status in deleted_files:
#         add_deleted_to_tree(tree, deleted_path, status)
#
#     return JsonResponse({"success": True, "tree": tree})
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/project_app/views/api/file_tree.py
# --------------------------------------------------------------------------------
