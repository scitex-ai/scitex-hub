#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/directory_views/helpers.py
# ----------------------------------------
"""
Helper Functions for Directory and File Views

This module provides shared utility functions used across directory browsing,
file viewing, and git integration views:

- Access control validation
- Filesystem manager setup
- Path security checks
- Breadcrumb generation
- Git metadata parsing
- Time formatting
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from datetime import datetime

from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger(__name__)


def _check_project_access(request, project, username, slug):
    """
    Validate user access to project and redirect if unauthorized.

    Args:
        request: Django request object
        project: Project instance
        username: Project owner username
        slug: Project slug

    Returns:
        HttpResponse redirect if no access, None if access granted
    """
    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
        or getattr(project, "visibility", None) == "public"
    )

    if not has_access:
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        else:
            messages.error(request, "You don't have permission to access this project.")
            return redirect("user_projects:detail", username=username, slug=slug)

    return None


def _get_project_filesystem(project, username, slug):
    """
    Get project filesystem manager and validate project path exists.

    Args:
        project: Project instance
        username: Project owner username
        slug: Project slug

    Returns:
        tuple: (manager, project_path) or (None, redirect_response)
    """
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        messages.error(None, "Project directory not found.")
        return None, redirect("user_projects:detail", username=username, slug=slug)

    return manager, project_path


def _validate_path_security(full_path, project_path, username, slug):
    """
    Ensure path is within project directory (prevent path traversal).

    Args:
        full_path: Full path to validate
        project_path: Project root path
        username: Project owner username
        slug: Project slug

    Returns:
        Path object if valid, redirect response if invalid
    """
    try:
        resolved_path = full_path.resolve()
        if not str(resolved_path).startswith(str(project_path.resolve())):
            messages.error(None, "Invalid directory path.")
            return redirect("user_projects:detail", username=username, slug=slug)
        return resolved_path
    except Exception:
        messages.error(None, "Invalid directory path.")
        return redirect("user_projects:detail", username=username, slug=slug)


def _build_file_breadcrumb(username, slug, file_path, project_name):
    """
    Build breadcrumb navigation for file view.

    Args:
        username: Project owner username
        slug: Project slug
        file_path: Relative file path
        project_name: Project name

    Returns:
        list: Breadcrumb items with name and url
    """
    breadcrumbs = [{"name": project_name, "url": f"/{username}/{slug}/"}]

    path_parts = file_path.split("/")
    current_path = ""
    for i, part in enumerate(path_parts):
        current_path += part
        if i < len(path_parts) - 1:
            current_path += "/"
            breadcrumbs.append(
                {"name": part, "url": f"/{username}/{slug}/{current_path}"}
            )
        else:
            breadcrumbs.append({"name": part, "url": None})

    return breadcrumbs


def _build_directory_breadcrumb(username, slug, directory_path, project_name):
    """
    Build breadcrumb navigation for directory view.

    Args:
        username: Project owner username
        slug: Project slug
        directory_path: Directory path string
        project_name: Project name

    Returns:
        list: Breadcrumb items with name, url, and is_last flag
    """
    breadcrumbs = [
        {"name": project_name, "url": f"/{username}/{slug}/", "is_last": False}
    ]

    path_parts = [p for p in directory_path.split("/") if p]
    current_path = ""
    for idx, part in enumerate(path_parts):
        current_path += part + "/"
        is_last = idx == len(path_parts) - 1
        breadcrumbs.append(
            {
                "name": part,
                "url": f"/{username}/{slug}/{current_path}",
                "is_last": is_last,
            }
        )

    return breadcrumbs


def _get_git_file_info(project_path, file_path, request, project):
    """
    Get git metadata for a file including commit info and branches.

    Args:
        project_path: Path to project root
        file_path: Relative file path
        request: Django request object
        project: Project instance

    Returns:
        dict: Git information including branches, commits, author, etc.
    """
    git_info = {}
    try:
        from apps.project_app.api_views_module.api_views import get_current_branch_from_session

        current_branch = get_current_branch_from_session(request, project)
        git_info["current_branch"] = current_branch

        # Get all branches
        all_branches_result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if all_branches_result.returncode == 0:
            branches = []
            for line in all_branches_result.stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith("*"):
                    branch_name = line.replace("remotes/origin/", "")
                    if branch_name and branch_name not in branches:
                        branches.append(branch_name)
                elif line.startswith("*"):
                    branch_name = line[2:].strip()
                    if branch_name not in branches:
                        branches.insert(0, branch_name)
            git_info["branches"] = branches
        else:
            git_info["branches"] = [git_info["current_branch"]]

        # Get last commit info for this specific file
        commit_result = subprocess.run(
            ["git", "log", "-1", "--format=%an|%ae|%ar|%at|%s|%h|%H", "--", file_path],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if commit_result.returncode == 0 and commit_result.stdout.strip():
            parts = commit_result.stdout.strip().split("|", 6)
            git_info.update(
                {
                    "author_name": parts[0],
                    "author_email": parts[1],
                    "time_ago": parts[2],
                    "timestamp": parts[3],
                    "message": parts[4],
                    "short_hash": parts[5],
                    "full_hash": parts[6] if len(parts) > 6 else parts[5],
                }
            )
        else:
            git_info.update(
                {
                    "author_name": "",
                    "author_email": "",
                    "time_ago": "Not committed",
                    "timestamp": "",
                    "message": "No commits yet",
                    "short_hash": "",
                    "full_hash": "",
                }
            )
    except Exception as e:
        logger.debug(f"Error getting git info for {file_path}: {e}")
        git_info = {
            "current_branch": "main",
            "branches": ["main"],
            "author_name": "",
            "author_email": "",
            "time_ago": "",
            "timestamp": "",
            "message": "",
            "short_hash": "",
            "full_hash": "",
        }

    return git_info


def _calculate_time_ago(timestamp):
    """
    Calculate human-readable time ago from Unix timestamp.

    Args:
        timestamp: Unix timestamp integer

    Returns:
        str: Human-readable time string (e.g., "2d ago", "3h ago")
    """
    delta = datetime.now() - datetime.fromtimestamp(timestamp)
    if delta.days > 365:
        return f"{delta.days // 365}y ago"
    elif delta.days > 30:
        return f"{delta.days // 30}mo ago"
    elif delta.days > 0:
        return f"{delta.days}d ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600}h ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60}m ago"
    else:
        return "just now"


def _parse_git_blame_porcelain(blame_stdout):
    """
    Parse git blame porcelain format output into structured data.

    Args:
        blame_stdout: Output from git blame --porcelain command

    Returns:
        list: Blame information dicts with commit, author, time, content
    """
    blame_lines = []
    lines = blame_stdout.split("\n")
    i = 0
    line_number = 1

    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue

        parts = lines[i].split()
        if len(parts) < 3:
            i += 1
            continue

        commit_hash = parts[0]
        blame_info = {
            'commit_hash': commit_hash,
            'short_hash': commit_hash[:7],
            'line_number': line_number,
            'author': '',
            'author_time': '',
            'author_time_ago': '',
            'summary': '',
            'content': '',
        }

        i += 1
        while i < len(lines) and not lines[i].startswith('\t'):
            if lines[i].startswith('author '):
                blame_info['author'] = lines[i][7:]
            elif lines[i].startswith('author-time '):
                timestamp = int(lines[i][12:])
                blame_info['author_time'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
                blame_info['author_time_ago'] = _calculate_time_ago(timestamp)
            elif lines[i].startswith('summary '):
                blame_info['summary'] = lines[i][8:]
            i += 1

        if i < len(lines) and lines[i].startswith('\t'):
            blame_info['content'] = lines[i][1:]
            i += 1

        blame_lines.append(blame_info)
        line_number += 1

    return blame_lines


def _parse_unified_diff(diff_stdout):
    """
    Parse unified diff format into structured line-by-line data.

    Args:
        diff_stdout: Output from git show/diff command

    Returns:
        list: Diff lines with content and type (header/hunk/addition/deletion/context)
    """
    diff_lines = []
    for diff_line in diff_stdout.split("\n"):
        line_type = "context"
        if diff_line.startswith("+++") or diff_line.startswith("---"):
            line_type = "header"
        elif diff_line.startswith("@@"):
            line_type = "hunk"
        elif diff_line.startswith("+"):
            line_type = "addition"
        elif diff_line.startswith("-"):
            line_type = "deletion"

        diff_lines.append({"content": diff_line, "type": line_type})

    return diff_lines


# EOF
