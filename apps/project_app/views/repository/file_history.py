#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/file_history.py
# ----------------------------------------
"""
Repository File History

Handles file history viewing functionality.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator

from apps.project_app.models import Project

logger = logging.getLogger(__name__)


def file_history_view(request, username, slug, branch, file_path):
    """
    Show commit history for a specific file (GitHub-style /commits/<branch>/<path>).

    Displays all commits that modified this file with:
    - Commit message, author, date, hash
    - File-specific stats (+/- lines)
    - Pagination (30 commits per page)
    - Filter by author or date range

    URLs:
    - /<username>/<project>/commits/<branch>/<file-path>
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access
    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
        or getattr(project, "visibility", None) == "public"
    )

    if not has_access:
        messages.error(request, "You don't have permission to access this file.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Get project path
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        messages.error(request, "Project directory not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Build breadcrumb
    breadcrumbs = [{"name": project.name, "url": f"/{username}/{slug}/"}]

    path_parts = file_path.split("/")
    current_path = ""
    for i, part in enumerate(path_parts):
        current_path += part
        if i < len(path_parts) - 1:  # Directory
            current_path += "/"
            breadcrumbs.append(
                {"name": part, "url": f"/{username}/{slug}/{current_path}"}
            )
        else:  # File
            breadcrumbs.append(
                {"name": part, "url": f"/{username}/{slug}/blob/{file_path}"}
            )

    # Get filter parameters
    author_filter = request.GET.get("author", "").strip()
    page_number = request.GET.get("page", 1)

    try:
        page_number = int(page_number)
    except (ValueError, TypeError):
        page_number = 1

    # Get file history using git log --follow
    commits = []
    try:
        # Build git log command
        # Format: hash|author_name|author_email|timestamp|relative_time|subject
        git_cmd = [
            "git",
            "log",
            "--follow",
            "--format=%H|%an|%ae|%at|%ar|%s",
            "--",
            file_path,
        ]

        # Add author filter if specified
        if author_filter:
            git_cmd.insert(3, f"--author={author_filter}")

        result = subprocess.run(
            git_cmd, cwd=project_path, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 5)
                if len(parts) < 6:
                    continue

                (
                    commit_hash,
                    author_name,
                    author_email,
                    timestamp,
                    relative_time,
                    subject,
                ) = parts

                # Get file-specific stats for this commit
                stats_result = subprocess.run(
                    [
                        "git",
                        "show",
                        "--numstat",
                        "--format=",
                        commit_hash,
                        "--",
                        file_path,
                    ],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                additions = 0
                deletions = 0
                if stats_result.returncode == 0 and stats_result.stdout.strip():
                    stat_line = stats_result.stdout.strip().split("\n")[0]
                    stat_parts = stat_line.split("\t")
                    if len(stat_parts) >= 2:
                        try:
                            additions = (
                                int(stat_parts[0]) if stat_parts[0] != "-" else 0
                            )
                            deletions = (
                                int(stat_parts[1]) if stat_parts[1] != "-" else 0
                            )
                        except ValueError:
                            pass

                commits.append(
                    {
                        "hash": commit_hash,
                        "short_hash": commit_hash[:7],
                        "author_name": author_name,
                        "author_email": author_email,
                        "timestamp": int(timestamp),
                        "relative_time": relative_time,
                        "subject": subject,
                        "additions": additions,
                        "deletions": deletions,
                    }
                )

    except subprocess.TimeoutExpired:
        logger.error(f"Git log timeout for {file_path} in {project.slug}")
        messages.error(request, "Timeout while fetching file history.")
    except Exception as e:
        logger.error(f"Error getting file history for {file_path}: {e}")
        messages.error(request, f"Error fetching file history: {str(e)}")

    # Pagination
    paginator = Paginator(commits, 30)
    commits_page = paginator.get_page(page_number)

    # Get unique authors for filter dropdown
    unique_authors = sorted(set(c["author_name"] for c in commits))

    context = {
        "project": project,
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "branch": branch,
        "breadcrumbs": breadcrumbs,
        "commits": commits_page,
        "unique_authors": unique_authors,
        "author_filter": author_filter,
        "total_commits": len(commits),
    }

    return render(request, "project_app/repository/file_history.html", context)


# EOF
