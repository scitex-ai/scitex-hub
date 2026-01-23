#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/api/directory_concatenation.py
# ----------------------------------------
"""
Directory Concatenation API Views

This module contains API endpoints for directory concatenation functionality.
Returns markdown-formatted content with tree + file contents (like view_repo.sh).
"""

from __future__ import annotations
import logging

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse

from ...models import Project

logger = logging.getLogger(__name__)


# ============================================================================
# Directory Concatenation API
# ============================================================================


@login_required
def api_concatenate_directory(request, username, slug, directory_path=""):
    """
    API endpoint to concatenate all files in a directory (like view_repo.sh).
    Returns markdown-formatted content with tree + file contents.
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access
    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
    )

    if not has_access:
        return JsonResponse({"success": False, "error": "Permission denied"})

    # Get directory path
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        return JsonResponse({"success": False, "error": "Project directory not found"})

    dir_path = project_path / directory_path

    # Security check
    try:
        dir_path = dir_path.resolve()
        if not str(dir_path).startswith(str(project_path.resolve())):
            return JsonResponse({"success": False, "error": "Invalid path"})
    except (ValueError, OSError, RuntimeError) as e:
        logger.warning(f"Path resolution failed: {e}")
        return JsonResponse({"success": False, "error": "Invalid path"})

    if not dir_path.exists() or not dir_path.is_dir():
        return JsonResponse({"success": False, "error": "Directory not found"})

    # Whitelist extensions
    WHITELIST_EXTS = {
        ".txt",
        ".md",
        ".org",
        ".sh",
        ".py",
        ".yaml",
        ".yml",
        ".json",
        ".tex",
        ".bib",
    }
    MAX_FILE_SIZE = 100000  # 100KB

    output = []
    output.append(
        f"# Directory View: {directory_path if directory_path else 'Project Root'}"
    )
    output.append(f"Project: {project.name}")
    output.append(f"Owner: {project.owner.username}")
    output.append(f"")
    output.append(f"## File Contents")
    output.append(f"")

    # Recursively get all files
    for file_path in sorted(dir_path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.name.startswith(".") and file_path.name not in [
            ".gitignore",
            ".gitkeep",
        ]:
            continue
        if file_path.suffix.lower() not in WHITELIST_EXTS:
            continue
        if file_path.stat().st_size > MAX_FILE_SIZE:
            continue

        try:
            rel_path = file_path.relative_to(dir_path)
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Get language for syntax highlighting
            lang_map = {
                ".py": "python",
                ".sh": "bash",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".json": "json",
                ".md": "markdown",
                ".tex": "latex",
            }
            lang = lang_map.get(file_path.suffix.lower(), "plaintext")

            output.append(f"### `{rel_path}`")
            output.append(f"")
            output.append(f"```{lang}")
            output.append(content[:5000])  # First 5000 chars
            if len(content) > 5000:
                output.append("...")
            output.append("```")
            output.append(f"")
        except Exception:
            continue

    concatenated_content = "\n".join(output)

    return JsonResponse(
        {
            "success": True,
            "content": concatenated_content,
            "file_count": len([l for l in output if l.startswith("###")]),
        }
    )


# EOF
