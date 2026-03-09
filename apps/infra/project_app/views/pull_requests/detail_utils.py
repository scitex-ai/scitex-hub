#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull Request Detail - Utility Functions."""

from __future__ import annotations

import logging
import subprocess
from itertools import chain
from operator import attrgetter

logger = logging.getLogger(__name__)


def get_pr_diff(project, pr):
    """
    Get diff for a PR.

    Returns:
        tuple: (diff_data: str, changed_files: list)
    """
    try:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        if not project_path or not project_path.exists():
            return None, []

        # Get full diff
        result = subprocess.run(
            ["git", "diff", f"{pr.target_branch}...{pr.source_branch}"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None, []

        diff_data = result.stdout

        # Get changed files
        changed_files = _get_changed_files(project_path, pr)
        return diff_data, changed_files

    except Exception as e:
        logger.error(f"Failed to get PR diff: {e}")
        return None, []


def _get_changed_files(project_path, pr):
    """Get list of changed files in a PR."""
    files_result = subprocess.run(
        ["git", "diff", "--name-status", f"{pr.target_branch}...{pr.source_branch}"],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    changed_files = []
    if files_result.returncode == 0:
        for line in files_result.stdout.split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 2:
                    changed_files.append({"status": parts[0], "path": parts[1]})

    return changed_files


def get_pr_checks(project, pr):
    """
    Get CI/CD checks status for a PR.

    Returns:
        list: Check results
    """
    # TODO: Implement integration with CI/CD system
    return []


def get_pr_timeline(pr):
    """
    Get merged timeline of comments and events.

    Returns:
        list: Timeline items sorted chronologically
    """
    comments = list(
        pr.comments.filter(parent_comment__isnull=True).select_related("author")
    )
    events = list(pr.events.select_related("actor"))

    # Merge and sort by created_at
    timeline = sorted(chain(comments, events), key=attrgetter("created_at"))
    return timeline


# EOF
