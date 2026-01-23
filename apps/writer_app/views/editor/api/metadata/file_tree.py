#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/file_tree.py
"""File tree API endpoint for writer app."""

from __future__ import annotations
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from apps.project_app.models import Project

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def file_tree_view(request, project_id=None):
    """API endpoint to get project file tree for writer sidebar navigation.

    Args:
        request: HTTP request
        project_id: Project ID from URL path

    Returns:
        JSON with file tree structure: {"success": True, "tree": [...]}
    """
    try:
        # Get project ID from URL or query params
        if not project_id:
            project_id = request.GET.get("project_id")

        if not project_id:
            return JsonResponse({
                "success": False,
                "error": "No project ID provided"
            })

        project = get_object_or_404(Project, id=project_id)

        # Check access (allow public access for public projects)
        if request.user.is_authenticated:
            has_access = (
                project.owner == request.user
                or project.collaborators.filter(id=request.user.id).exists()
                or project.visibility == "public"
            )
        else:
            # For visitor users, check if this is their allocated visitor project
            visitor_project_id = request.session.get("visitor_project_id")
            has_access = (
                project.visibility == "public"
                or (visitor_project_id and project.id == visitor_project_id)
            )

        if not has_access:
            return JsonResponse({"success": False, "error": "Permission denied"})

        # Get project directory
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        if not project_path or not project_path.exists():
            return JsonResponse({
                "success": False,
                "error": "Project directory not found"
            })

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
                    item_data = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": str(rel_path),
                    }

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

    except Exception as e:
        logger.error(f"Error getting file tree: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": str(e)
        })


# EOF
