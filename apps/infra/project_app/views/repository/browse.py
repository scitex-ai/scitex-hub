#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/repository/browse.py
# ----------------------------------------
"""
Repository Browse Views

Handles directory browsing functionality for projects.
"""

from __future__ import annotations

import logging
import subprocess

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


def project_directory_dynamic(request, username, slug, directory_path):
    """
    Dynamic directory browser - handles ANY directory path.

    URLs like:
    - /username/project/scripts/
    - /username/project/scripts/mnist/
    - /username/project/paper/manuscript/
    - /username/project/data/raw/images/
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access permissions
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
            return redirect("project_app:detail", username=username, slug=slug)

    # Get project path
    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        messages.error(request, "Project directory not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Construct full directory path
    full_directory_path = project_path / directory_path

    # Security check: ensure path is within project directory
    try:
        full_directory_path = full_directory_path.resolve()
        if not str(full_directory_path).startswith(str(project_path.resolve())):
            messages.error(request, "Invalid directory path.")
            return redirect("project_app:detail", username=username, slug=slug)
    except Exception:
        messages.error(request, "Invalid directory path.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Check if directory exists
    if not full_directory_path.exists():
        messages.error(request, f"Directory '{directory_path}' not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Get directory contents
    contents = []
    try:
        for item in full_directory_path.iterdir():
            # Show all files and directories including hidden files
            # Skip only special directories like .git
            if item.is_dir() and item.name in [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
            ]:
                continue

            if item.is_file():
                contents.append(
                    {
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "path": str(item.relative_to(project_path)),
                    }
                )
            elif item.is_dir():
                contents.append(
                    {
                        "name": item.name,
                        "type": "directory",
                        "path": str(item.relative_to(project_path)),
                    }
                )
    except PermissionError:
        messages.error(request, "Permission denied accessing directory.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Sort: directories first, then files, alphabetically
    contents.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))

    # Build breadcrumb navigation
    breadcrumbs = [
        {"name": project.name, "url": f"/{username}/{slug}/", "is_last": False}
    ]

    # Add each path component to breadcrumbs
    path_parts = [p for p in directory_path.split("/") if p]  # Filter empty strings
    current_path = ""
    for idx, part in enumerate(path_parts):
        current_path += part + "/"
        is_last = idx == len(path_parts) - 1  # Last item in the path
        breadcrumbs.append(
            {
                "name": part,
                "url": f"/{username}/{slug}/{current_path}",
                "is_last": is_last,
            }
        )

    context = {
        "project": project,
        "directory": path_parts[0] if path_parts else directory_path,
        "subpath": "/".join(path_parts[1:]) if len(path_parts) > 1 else None,
        "breadcrumb_path": directory_path,
        "contents": contents,
        "breadcrumbs": breadcrumbs,
        "can_edit": project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists(),
    }

    return render(request, "project_app/repository/directory_browser.html", context)


def project_directory(request, username, slug, directory, subpath=None):
    """
    Browse scientific workflow directories within a project.

    URLs like:
    - /username/project-name/scripts/
    - /username/project-name/scripts/analysis/
    - /username/project-name/data/raw/
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access permissions
    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
        or project.visibility == "public"
    )

    if not has_access:
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        else:
            messages.error(request, "You don't have permission to access this project.")
            return redirect("project_app:detail", username=username, slug=slug)

    # Get the project directory manager
    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        messages.error(request, "Project directory not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Construct the full directory path
    if subpath:
        directory_path = project_path / directory / subpath
        breadcrumb_path = f"{directory}/{subpath}"
    else:
        directory_path = project_path / directory
        breadcrumb_path = directory

    # Security check: ensure path is within project directory
    try:
        directory_path = directory_path.resolve()
        if not str(directory_path).startswith(str(project_path.resolve())):
            messages.error(request, "Invalid directory path.")
            return redirect("project_app:detail", username=username, slug=slug)
    except Exception:
        messages.error(request, "Invalid directory path.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Check if directory exists
    if not directory_path.exists():
        messages.error(request, f"Directory '{breadcrumb_path}' not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Get directory contents
    contents = []
    try:
        # Helper function to get git commit info for a file/folder
        def get_git_info(path):
            """Get last commit message, author, hash, and time for a file/folder"""
            try:
                # Get last commit for this file (including hash)
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "-1",
                        "--format=%an|%ar|%s|%h",
                        "--",
                        str(path.name),
                    ],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0 and result.stdout.strip():
                    author, time_ago, message, commit_hash = (
                        result.stdout.strip().split("|", 3)
                    )
                    return {
                        "author": author,
                        "time_ago": time_ago,
                        "message": message[:80],  # Truncate to 80 chars
                        "hash": commit_hash,
                    }
            except Exception as e:
                logger.debug(f"Error getting git info for {path}: {e}")

            return {"author": "", "time_ago": "", "message": "", "hash": ""}

        for item in directory_path.iterdir():
            # Show all files and directories including dotfiles
            git_info = get_git_info(item)

            if item.is_file():
                contents.append(
                    {
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "path": str(item.relative_to(project_path)),
                        "author": git_info.get("author", ""),
                        "time_ago": git_info.get("time_ago", ""),
                        "message": git_info.get("message", ""),
                        "hash": git_info.get("hash", ""),
                    }
                )
            elif item.is_dir():
                contents.append(
                    {
                        "name": item.name,
                        "type": "directory",
                        "path": str(item.relative_to(project_path)),
                        "author": git_info.get("author", ""),
                        "time_ago": git_info.get("time_ago", ""),
                        "message": git_info.get("message", ""),
                        "hash": git_info.get("hash", ""),
                    }
                )
    except PermissionError:
        messages.error(request, "Permission denied accessing directory.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Sort contents: directories first, then files, both alphabetically
    contents.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))

    # Build breadcrumb navigation
    breadcrumbs = [
        {"name": project.name, "url": project.get_absolute_url()},
        {
            "name": directory,
            "url": f"{project.get_absolute_url()}{directory}/",
        },
    ]

    if subpath:
        path_parts = subpath.split("/")
        current_path = directory
        for part in path_parts:
            current_path += f"/{part}"
            breadcrumbs.append(
                {
                    "name": part,
                    "url": f"{project.get_absolute_url()}{current_path}/",
                }
            )

    context = {
        "project": project,
        "directory": directory,
        "subpath": subpath,
        "breadcrumb_path": breadcrumb_path,
        "contents": contents,
        "breadcrumbs": breadcrumbs,
        "can_edit": project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists(),
    }

    return render(request, "project_app/repository/directory_browser.html", context)


# EOF
