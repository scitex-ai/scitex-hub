#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/api/file_tree.py
# ----------------------------------------
"""
File Tree Navigation API

This module contains API endpoints for navigating project file structure.
"""

from __future__ import annotations
import logging
import subprocess

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....models import Project
from .permissions import check_project_read_access

logger = logging.getLogger(__name__)


def _get_git_status_map(project_path) -> dict[str, dict[str, any]]:
    """
    Get git status for all files as a dictionary.

    Returns:
        Dict mapping file paths to {status: str, staged: bool}
    """
    status_map = {}

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return status_map

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            status_code = line[:2]
            filepath = line[3:].strip()

            # Remove quotes if present
            if filepath.startswith('"') and filepath.endswith('"'):
                filepath = filepath[1:-1]

            # Determine status code for display
            index_status = status_code[0]
            worktree_status = status_code[1]

            if index_status == "?" or worktree_status == "?":
                display_status = "??"
                staged = False
            elif index_status == "A":
                display_status = "A"
                staged = True
            elif index_status == "D" or worktree_status == "D":
                display_status = "D"
                staged = index_status == "D"
            elif index_status == "M" or worktree_status == "M":
                display_status = "M"
                staged = index_status == "M"
            elif index_status == "R":
                display_status = "R"
                staged = True
            else:
                display_status = status_code.strip() or "M"
                staged = index_status != " "

            status_map[filepath] = {"status": display_status, "staged": staged}

            # Also add parent directories as modified (to show git gutter on directories)
            parts = filepath.split("/")
            for i in range(1, len(parts)):
                parent = "/".join(parts[:i])
                if parent not in status_map:
                    status_map[parent] = {"status": "M", "staged": False}

    except (subprocess.TimeoutExpired, Exception) as e:
        logger.debug(f"Could not get git status: {e}")

    return status_map


@require_http_methods(["GET"])
def api_file_tree(request, username, slug):
    """API endpoint to get project file tree for sidebar navigation"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access
    if not check_project_read_access(request, project):
        return JsonResponse({"success": False, "error": "Permission denied"})

    # Get project directory (works for both local and remote projects)
    from apps.project_app.services.project_service_manager import ProjectServiceManager

    try:
        service_manager = ProjectServiceManager(project)
        project_path = service_manager.get_project_path()
    except Exception as e:
        logger.error(f"Failed to get project path for {username}/{slug}: {e}")
        return JsonResponse({"success": False, "error": f"Failed to access project: {str(e)}"})

    if not project_path or not project_path.exists():
        return JsonResponse({"success": False, "error": "Project directory not found"})

    # Get git status map for all files
    git_status_map = _get_git_status_map(project_path)

    def build_tree(path, max_depth=5, current_depth=0):
        """Build file tree recursively (deeper for full navigation)"""
        items = []
        try:
            for item in sorted(
                path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            ):
                # Skip hidden files except .git directory, .gitignore, and .gitkeep
                if item.name.startswith(".") and item.name not in [
                    ".git",
                    ".gitignore",
                    ".gitkeep",
                ]:
                    continue
                # Skip common non-essential directories
                if item.name in [
                    "__pycache__",
                    "node_modules",
                    ".venv",
                    "venv",
                ]:
                    continue

                rel_path = item.relative_to(project_path)
                rel_path_str = str(rel_path)

                # Detect symlinks
                is_symlink = item.is_symlink()
                symlink_target = None
                if is_symlink:
                    try:
                        # Get symlink target relative to the symlink location
                        target = item.readlink()
                        symlink_target = str(target)
                        logger.debug(f"Symlink detected: {item.name} -> {symlink_target}")
                    except (OSError, ValueError) as e:
                        logger.warning(f"Failed to read symlink target for {item.name}: {e}")
                        symlink_target = None

                item_data = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": rel_path_str,
                    "is_symlink": is_symlink,
                }

                # Add git status if available
                if rel_path_str in git_status_map:
                    item_data["git_status"] = git_status_map[rel_path_str]

                # Add symlink target if available
                if symlink_target:
                    item_data["symlink_target"] = symlink_target

                # Add children for directories (deeper depth for full tree)
                if item.is_dir() and current_depth < max_depth:
                    item_data["children"] = build_tree(
                        item, max_depth, current_depth + 1
                    )

                items.append(item_data)
        except PermissionError:
            pass

        return items

    tree = build_tree(project_path)

    return JsonResponse({"success": True, "tree": tree})


# EOF
