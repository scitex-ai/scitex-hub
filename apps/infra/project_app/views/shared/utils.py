#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Utility Functions

Common helper functions used across multiple features.
"""

import logging

logger = logging.getLogger(__name__)


def get_git_commit_info(project_path, file_path):
    """
    Get last commit information for a file or directory

    Args:
        project_path: Path to project root
        file_path: Relative path to file/directory

    Returns:
        dict: Commit info with author, time_ago, message, hash
    """
    try:
        import subprocess

        result = subprocess.run(
            ["git", "log", "-1", "--format=%an|%ar|%s|%h", "--", str(file_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            author, time_ago, message, commit_hash = result.stdout.strip().split("|", 3)
            return {
                "author": author,
                "time_ago": time_ago,
                "message": message[:80],  # Truncate to 80 chars
                "hash": commit_hash,
            }
    except Exception as e:
        logger.debug(f"Error getting git info for {file_path}: {e}")

    return {"author": "", "time_ago": "", "message": "", "hash": ""}


def format_file_size(size_bytes):
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size (e.g., "1.5 KB", "2.3 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_available_branches(project_path):
    """
    Get list of available Git branches

    Args:
        project_path: Path to project root

    Returns:
        tuple: (branches list, current_branch)
    """
    import subprocess

    branches = []
    current_branch = "develop"

    if not project_path or not project_path.exists():
        return branches, current_branch

    try:
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line:
                    # Remove * prefix and remotes/origin/ prefix
                    branch = line.replace("*", "").strip()
                    branch = branch.replace("remotes/origin/", "")
                    if branch and branch not in branches:
                        branches.append(branch)
                    # Check if this is the current branch
                    if line.startswith("*"):
                        current_branch = branch
    except Exception as e:
        logger.debug(f"Error getting branches: {e}")

    if not branches:
        branches = [current_branch]

    return branches, current_branch


# EOF
