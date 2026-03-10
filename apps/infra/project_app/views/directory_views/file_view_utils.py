#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File view utility functions.

Provides common utilities for file view operations:
- File path validation
- Git information retrieval
- Breadcrumb building
"""

from __future__ import annotations

import logging
import subprocess

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from ...models import Project

logger = logging.getLogger(__name__)


def get_file_context(request, username, slug, file_path):
    """
    Get common file context including project, paths, and access validation.

    Returns:
        tuple: (user, project, project_path, full_file_path) or None if invalid
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        return None

    full_file_path = project_path / file_path

    # Security check
    try:
        full_file_path = full_file_path.resolve()
        if not str(full_file_path).startswith(str(project_path.resolve())):
            return None
    except Exception:
        return None

    if not full_file_path.exists() or not full_file_path.is_file():
        return None

    return user, project, project_path, full_file_path


def get_git_info(request, project, project_path, file_path):
    """
    Get Git commit information for a file.

    Returns:
        dict: Git info including branch, author, commit message, etc.
    """
    git_info = {}
    try:
        from apps.infra.project_app.api_views_module.api_views import (
            get_current_branch_from_session,
        )

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
            [
                "git",
                "log",
                "-1",
                "--format=%an|%ae|%ar|%at|%s|%h|%H",
                "--",
                file_path,
            ],
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


def build_breadcrumbs(project, username, slug, file_path):
    """
    Build breadcrumb navigation for file path.

    Returns:
        list: List of breadcrumb dicts with name and url
    """
    breadcrumbs = [{"name": project.name, "url": f"/{username}/{slug}/"}]
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


# EOF
