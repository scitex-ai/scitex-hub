#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Detail Helper Functions

Utilities for fetching repository file information and README content.
"""

import logging
import subprocess

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
            author, time_ago, message, commit_hash = result.stdout.strip().split("|", 3)
            return {
                "author": author,
                "time_ago": time_ago,
                "message": message[:80],  # Truncate to 80 chars
                "hash": commit_hash,
            }
    except Exception as e:
        logger.debug(f"Error getting git info for {path}: {e}")

    return {"author": "", "time_ago": "", "message": "", "hash": ""}


def get_batch_git_info(project_path, names):
    """
    Get git info for multiple files/dirs in a single subprocess call.

    Runs one `git log` with --name-only over recent commits to find the last
    commit touching each requested name.  This replaces N individual `git log
    -1` calls with a single call, dramatically reducing subprocess overhead.

    Args:
        project_path: Root path of the project (Path or str)
        names: Iterable of file/directory base-names to look up

    Returns:
        dict mapping each name to {author, time_ago, message, hash}.
        Names with no git history are absent from the dict.
    """
    names = list(names)
    if not names:
        return {}

    result = {}
    names_set = set(names)

    try:
        # Fetch enough recent commits so every file is likely covered.
        # Using len*3 gives a reasonable budget; fall back to individual
        # lookups for anything still missing afterwards.
        depth = max(len(names) * 3, 30)
        proc = subprocess.run(
            [
                "git",
                "log",
                "--format=%an|%ar|%s|%h",
                "--name-only",
                "-n",
                str(depth),
                "--",
            ]
            + names,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if proc.returncode != 0:
            return {}

        current_info = None
        for line in proc.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # Commit header lines have exactly 3 "|" separators from our format
            parts = stripped.split("|", 3)
            if len(parts) == 4:
                current_info = {
                    "author": parts[0],
                    "time_ago": parts[1],
                    "message": parts[2][:80],
                    "hash": parts[3],
                }
            elif current_info is not None:
                # This is a filename produced by --name-only
                basename = stripped.split("/")[-1]
                if basename in names_set and basename not in result:
                    result[basename] = current_info
                    if len(result) == len(names_set):
                        break  # All files accounted for

    except Exception as exc:
        logger.debug(f"Error in get_batch_git_info: {exc}")

    return result


def get_directory_contents(project_path, skip_git=False):
    """
    Get files and directories in project root with git info.

    Args:
        project_path: Root path of the project
        skip_git: If True, skip git info lookups (for remote/trip projects)

    Returns:
        tuple: (files_list, dirs_list)
    """
    files = []
    dirs = []
    empty_git = {"author": "", "time_ago": "", "message": "", "hash": ""}

    if not project_path or not project_path.exists():
        return files, dirs

    try:
        items = list(project_path.iterdir())

        # Batch-fetch git info for all items in a single subprocess call
        if skip_git:
            batch_git = {}
        else:
            all_names = [item.name for item in items]
            batch_git = get_batch_git_info(project_path, all_names)

        for item in items:
            git_info = batch_git.get(item.name, empty_git)

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
