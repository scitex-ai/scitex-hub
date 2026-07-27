#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/repository/commit_detail.py
# ----------------------------------------
"""
Repository Commit Detail

Handles commit detail viewing functionality.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.git_ref_validation import (
    END_OF_OPTIONS,
    is_valid_git_ref,
)

logger = logging.getLogger(__name__)


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

    # ``commit_hash`` comes straight from the URL (``<str:commit_hash>`` =
    # ``[^/]+``, which PERMITS a leading ``-``) and is handed to ``git show`` /
    # ``git diff-tree`` in a rev position. A value such as
    # ``--output=/abs/path`` would be parsed by git as an option and truncate
    # an arbitrary host file. Reject anything that is not a plain revision.
    if not is_valid_git_ref(commit_hash):
        messages.error(request, "Invalid commit reference.")
        return redirect("project_app:detail", username=username, slug=slug)

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
                END_OF_OPTIONS,
                commit_hash,
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            messages.error(request, f"Commit {commit_hash} not found.")
            return redirect("project_app:detail", username=username, slug=slug)

        parts = result.stdout.strip().split("|", 6)
        commit_info = {
            "author_name": parts[0],
            "author_email": parts[1],
            "date": datetime.fromisoformat(parts[2].replace("Z", "+00:00")),
            "subject": parts[3],  # First line of commit message
            "body": parts[4] if len(parts) > 4 else "",  # Full commit message body
            "parent_hash": (
                parts[5].split()[0] if len(parts) > 5 and parts[5] else None
            ),  # First parent
            "full_hash": parts[6] if len(parts) > 6 else commit_hash,
            "short_hash": commit_hash[:7],
        }

        # Get list of changed files with stats
        stats_result = subprocess.run(
            [
                "git",
                "diff-tree",
                "--no-commit-id",
                "--numstat",
                "-r",
                END_OF_OPTIONS,
                commit_hash,
            ],
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
                        [
                            "git",
                            "show",
                            "--format=",
                            END_OF_OPTIONS,
                            commit_hash,
                            "--",
                            filepath,
                        ],
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
        return redirect("project_app:detail", username=username, slug=slug)
    except Exception as e:
        logger.error(f"Error fetching commit details: {e}")
        messages.error(request, f"Error fetching commit details: {e}")
        return redirect("project_app:detail", username=username, slug=slug)

    context = {
        "project": project,
        "commit": commit_info,
        "changed_files": changed_files,
        "total_additions": sum(
            (
                int(f["additions"])
                if isinstance(f["additions"], (int, str))
                and str(f["additions"]).isdigit()
                else 0
            )
            for f in changed_files
        ),
        "total_deletions": sum(
            (
                int(f["deletions"])
                if isinstance(f["deletions"], (int, str))
                and str(f["deletions"]).isdigit()
                else 0
            )
            for f in changed_files
        ),
    }

    return render(request, "project_app/repository/commit_detail.html", context)


# EOF
