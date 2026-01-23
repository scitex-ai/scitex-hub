#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/directory_views/history.py
# ----------------------------------------
"""
File History and Commit Detail Views Module

This module contains views for displaying file history and commit details:
- file_history_view: Show commit history for a specific file
- commit_detail: Show detailed diff and metadata for a commit
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from ...models import Project

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
        return redirect("user_projects:detail", username=username, slug=slug)

    # Get project path
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        messages.error(request, "Project directory not found.")
        return redirect("user_projects:detail", username=username, slug=slug)

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


def commit_detail(request, username, slug, commit_hash):
    """
    GitHub-style commit detail page showing diff and metadata.

    URL: /<username>/<slug>/commit/<commit_hash>/

    Shows:
    - Commit metadata (author, date, message)
    - Changed files with stats
    - Unified diffs for each file
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
            return redirect("user_projects:detail", username=username, slug=slug)

    # Get project path
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        messages.error(request, "Project directory not found.")
        return redirect("user_projects:detail", username=username, slug=slug)

    # Fetch commit information using git
    commit_info = {}
    changed_files = []

    try:
        # Get commit metadata: author, email, date, message
        result = subprocess.run(
            [
                "git",
                "show",
                "--no-patch",
                "--format=%an|%ae|%aI|%s|%b|%P|%H",
                commit_hash,
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            messages.error(request, f"Commit {commit_hash} not found.")
            return redirect("user_projects:detail", username=username, slug=slug)

        parts = result.stdout.strip().split("|", 6)
        commit_info = {
            "author_name": parts[0],
            "author_email": parts[1],
            "date": datetime.fromisoformat(parts[2].replace("Z", "+00:00")),
            "subject": parts[3],  # First line of commit message
            "body": parts[4] if len(parts) > 4 else "",  # Full commit message body
            "parent_hash": parts[5].split()[0]
            if len(parts) > 5 and parts[5]
            else None,  # First parent
            "full_hash": parts[6] if len(parts) > 6 else commit_hash,
            "short_hash": commit_hash[:7],
        }

        # Get list of changed files with stats
        stats_result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--numstat", "-r", commit_hash],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if stats_result.returncode == 0:
            for line in stats_result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    added = parts[0]
                    deleted = parts[1]
                    filepath = parts[2]

                    # Get the actual diff for this file
                    diff_result = subprocess.run(
                        ["git", "show", "--format=", commit_hash, "--", filepath],
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    # Parse unified diff to get line-by-line changes
                    diff_lines = []
                    if diff_result.returncode == 0 and diff_result.stdout:
                        for diff_line in diff_result.stdout.split("\n"):
                            line_type = "context"
                            if diff_line.startswith("+++") or diff_line.startswith(
                                "---"
                            ):
                                line_type = "header"
                            elif diff_line.startswith("@@"):
                                line_type = "hunk"
                            elif diff_line.startswith("+"):
                                line_type = "addition"
                            elif diff_line.startswith("-"):
                                line_type = "deletion"

                            diff_lines.append({"content": diff_line, "type": line_type})

                    # Determine file extension for syntax highlighting hint
                    file_ext = Path(filepath).suffix.lower()

                    changed_files.append(
                        {
                            "path": filepath,
                            "additions": added if added != "-" else 0,
                            "deletions": deleted if deleted != "-" else 0,
                            "diff": diff_lines,
                            "extension": file_ext,
                        }
                    )

        # Get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch_result.returncode == 0:
            commit_info["current_branch"] = branch_result.stdout.strip() or "main"
        else:
            commit_info["current_branch"] = "main"

    except subprocess.TimeoutExpired:
        messages.error(request, "Git command timed out.")
        return redirect("user_projects:detail", username=username, slug=slug)
    except Exception as e:
        logger.error(f"Error fetching commit details: {e}")
        messages.error(request, f"Error fetching commit details: {e}")
        return redirect("user_projects:detail", username=username, slug=slug)

    context = {
        "project": project,
        "commit": commit_info,
        "changed_files": changed_files,
        "total_additions": sum(
            int(f["additions"])
            if isinstance(f["additions"], (int, str)) and str(f["additions"]).isdigit()
            else 0
            for f in changed_files
        ),
        "total_deletions": sum(
            int(f["deletions"])
            if isinstance(f["deletions"], (int, str)) and str(f["deletions"]).isdigit()
            else 0
            for f in changed_files
        ),
    }

    return render(request, "project_app/repository/commit_detail.html", context)


# EOF
