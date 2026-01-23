#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/api/git_status.py
# ----------------------------------------
"""
Git Status API

This module contains API endpoints for retrieving git status information.
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


def _parse_git_file_status(status_code: str) -> tuple[str, bool]:
    """
    Parse git status code and return (status, staged) tuple.

    Args:
        status_code: Two-character git status code (e.g., "M ", " M", "??")

    Returns:
        Tuple of (status_string, is_staged_boolean)
    """
    index_status = status_code[0]
    worktree_status = status_code[1]

    status = "modified"
    staged = False

    if index_status == "?" or worktree_status == "?":
        status = "untracked"
    elif index_status == "A" or worktree_status == "A":
        status = "added"
        staged = index_status == "A"
    elif index_status == "D" or worktree_status == "D":
        status = "deleted"
        staged = index_status == "D"
    elif index_status == "R":
        status = "renamed"
        staged = True
    elif index_status == "C":
        status = "copied"
        staged = True
    elif index_status == "M" or worktree_status == "M":
        status = "modified"
        staged = index_status == "M"

    return status, staged


def _get_file_changes(filepath: str, project_path) -> int:
    """
    Get number of changes (additions + deletions) for a file.

    Args:
        filepath: Path to the file
        project_path: Project root path

    Returns:
        Total number of changes (additions + deletions)
    """
    changes = 0
    try:
        diff_result = subprocess.run(
            ["git", "diff", "--numstat", "--", filepath],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if diff_result.returncode == 0 and diff_result.stdout.strip():
            parts = diff_result.stdout.strip().split("\t")
            if len(parts) >= 2:
                try:
                    additions = int(parts[0]) if parts[0] != "-" else 0
                    deletions = int(parts[1]) if parts[1] != "-" else 0
                    changes = additions + deletions
                except ValueError:
                    pass
    except subprocess.TimeoutExpired:
        pass

    return changes


@require_http_methods(["GET"])
def api_git_status(request, username, slug):
    """
    API endpoint to get git status for all files in the project.
    Returns status of modified, added, deleted, and untracked files.
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access
    if not check_project_read_access(request, project):
        return JsonResponse({"success": False, "error": "Permission denied"})

    # Get project directory
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        return JsonResponse({"success": False, "error": "Project directory not found"})

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        current_branch = (
            branch_result.stdout.strip()
            if branch_result.returncode == 0
            else "unknown"
        )

        # Get ahead/behind count
        ahead = 0
        behind = 0
        try:
            ahead_behind_result = subprocess.run(
                [
                    "git",
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"HEAD...origin/{current_branch}",
                ],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if ahead_behind_result.returncode == 0:
                parts = ahead_behind_result.stdout.strip().split()
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
        except (subprocess.TimeoutExpired, ValueError):
            pass

        # Get git status (porcelain format for easy parsing)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Failed to get git status",
                    "branch": current_branch,
                }
            )

        # Parse git status output
        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            # Git status porcelain format:
            # XY filename
            # X = index status, Y = working tree status
            status_code = line[:2]
            filepath = line[3:].strip()

            # Remove quotes if present
            if filepath.startswith('"') and filepath.endswith('"'):
                filepath = filepath[1:-1]

            # Determine status
            status, staged = _parse_git_file_status(status_code)

            # Get number of changes for this file (if it's a text file)
            changes = _get_file_changes(filepath, project_path)

            files.append(
                {"path": filepath, "status": status, "staged": staged, "changes": changes}
            )

        return JsonResponse(
            {
                "success": True,
                "files": files,
                "branch": current_branch,
                "ahead": ahead,
                "behind": behind,
            }
        )

    except subprocess.TimeoutExpired:
        return JsonResponse({"success": False, "error": "Git command timed out"})
    except Exception as e:
        logger.error(f"Error getting git status: {e}")
        return JsonResponse({"success": False, "error": str(e)})


# EOF
