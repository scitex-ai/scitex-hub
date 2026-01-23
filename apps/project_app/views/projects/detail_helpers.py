#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Detail Helper Functions

Utilities for fetching repository file information and README content.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_git_info(path, project_path):
    """
    Get last commit message, author, hash, and time for a file/folder.

    Args:
        path: Path to file or directory
        project_path: Root path of the project

    Returns:
        dict: Git information with author, time_ago, message, hash
    """
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


def get_directory_contents(project_path):
    """
    Get files and directories in project root with git info.

    Args:
        project_path: Root path of the project

    Returns:
        tuple: (files_list, dirs_list)
    """
    files = []
    dirs = []

    if not project_path or not project_path.exists():
        return files, dirs

    try:
        for item in project_path.iterdir():
            # Show all files including dotfiles
            git_info = get_git_info(item, project_path)

            if item.is_file():
                files.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(project_path)),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "author": git_info.get("author", ""),
                        "time_ago": git_info.get("time_ago", ""),
                        "message": git_info.get("message", ""),
                        "hash": git_info.get("hash", ""),
                    }
                )
            elif item.is_dir():
                dirs.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(project_path)),
                        "author": git_info.get("author", ""),
                        "time_ago": git_info.get("time_ago", ""),
                        "message": git_info.get("message", ""),
                        "hash": git_info.get("hash", ""),
                    }
                )
    except Exception:
        pass

    # Sort: directories first, then files
    dirs.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())

    return files, dirs


def get_readme_content(project_path):
    """
    Get README.md content converted to HTML if exists.

    Args:
        project_path: Root path of the project

    Returns:
        tuple: (readme_content, readme_html)
    """
    readme_content = None
    readme_html = None

    if not project_path or not project_path.exists():
        return readme_content, readme_html

    try:
        readme_path = project_path / "README.md"
        if readme_path.exists():
            readme_content = readme_path.read_text(encoding="utf-8")
            # Convert markdown to HTML
            import markdown
            readme_html = markdown.markdown(
                readme_content,
                extensions=["fenced_code", "tables", "nl2br"],
            )
    except Exception:
        pass

    return readme_content, readme_html


def get_branches(project_path, current_branch):
    """
    Get list of git branches from project.

    Args:
        project_path: Root path of the project
        current_branch: Default current branch

    Returns:
        tuple: (branches_list, current_branch)
    """
    branches = []

    if not project_path or not project_path.exists():
        return [current_branch] if current_branch else ["develop"], current_branch

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
        branches = [current_branch] if current_branch else ["develop"]

    return branches, current_branch


# EOF
