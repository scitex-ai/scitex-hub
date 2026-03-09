#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 20:15:00 (ywatanabe)"
# File: ./apps/workspace_app/git_operations.py

"""
Git operations for SciTeX Cloud

Provides helper functions for git operations on Django projects
that are backed by Gitea repositories.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


def git_commit_and_push(
    project_dir: Path,
    message: str,
    files: Optional[List[str]] = None,
    branch: str = "develop",
    push: bool = True,
) -> Tuple[bool, str]:
    """
    Commit changes and optionally push to Gitea.

    Args:
        project_dir: Path to project directory (must be a git repo)
        message: Commit message
        files: List of files to commit (None = all changes)
        branch: Branch name (default: develop)
        push: Whether to push to remote (default: True)

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        project_dir = Path(project_dir)

        if not (project_dir / ".git").exists():
            return False, f"Not a git repository: {project_dir}"

        # Add files
        if files:
            for file in files:
                result = subprocess.run(
                    ["git", "add", file],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return False, f"git add failed: {result.stderr}"
        else:
            # Add all changes
            result = subprocess.run(
                ["git", "add", "."], cwd=project_dir, capture_output=True, text=True
            )
            if result.returncode != 0:
                return False, f"git add failed: {result.stderr}"

        # Check if there are changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if not status.stdout.strip():
            return True, "No changes to commit"

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return False, f"git commit failed: {result.stderr}"

        commit_output = result.stdout

        # Push to remote
        if push:
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                # If push fails, commit is still local
                return (
                    False,
                    f"git push failed: {result.stderr}\nCommit succeeded locally: {commit_output}",
                )

            return True, f"✓ Committed and pushed to {branch}\n{commit_output}"

        return True, f"✓ Committed locally\n{commit_output}"

    except subprocess.TimeoutExpired:
        return False, "git push timeout"
    except Exception as e:
        logger.exception(f"Git operation failed for {project_dir}")
        return False, str(e)


def git_pull(project_dir: Path, branch: str = "develop") -> Tuple[bool, str]:
    """
    Pull latest changes from Gitea.

    Args:
        project_dir: Path to project directory
        branch: Branch to pull from

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        project_dir = Path(project_dir)

        if not (project_dir / ".git").exists():
            return False, f"Not a git repository: {project_dir}"

        # Fetch first
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return False, f"git fetch failed: {result.stderr}"

        # Pull
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return False, f"git pull failed: {result.stderr}"

        return True, result.stdout

    except subprocess.TimeoutExpired:
        return False, "git pull timeout"
    except Exception as e:
        logger.exception(f"Git pull failed for {project_dir}")
        return False, str(e)


def configure_git_credentials(project_dir: Path, username: str, token: str):
    """
    Configure git credentials for pushing to Gitea.

    Sets up credential helper to use token authentication.

    Args:
        project_dir: Path to project directory
        username: Gitea username
        token: Gitea API token
    """
    try:
        project_dir = Path(project_dir)

        # Get current remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Failed to get remote URL: {result.stderr}")
            return False

        origin_url = result.stdout.strip()

        # Update URL to include credentials
        if origin_url.startswith("http"):
            # Extract base URL
            if "@" in origin_url:
                # Remove existing credentials
                origin_url = "http://" + origin_url.split("@")[1]

            # Add token authentication
            gitea_url = settings.GITEA_URL.replace("http://", "")
            auth_url = f"http://{username}:{token}@{gitea_url}"
            new_url = origin_url.replace(f"http://{gitea_url}", auth_url).replace(
                f"https://{gitea_url}", auth_url
            )

            # Set new remote URL
            subprocess.run(
                ["git", "remote", "set-url", "origin", new_url],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            logger.info(f"✓ Configured git credentials for {project_dir}")
            return True

    except Exception as e:
        logger.error(f"Failed to configure git credentials: {e}")
        return False


def auto_commit_file(
    project_dir: Path, filepath: str, message: str = None
) -> Tuple[bool, str]:
    """
    Automatically commit and push a single file.

    Useful for Writer and Scholar modules when files are edited.

    Args:
        project_dir: Path to project directory
        filepath: Relative path to file (e.g., 'paper/manuscript.tex')
        message: Commit message (auto-generated if None)

    Returns:
        Tuple of (success: bool, output: str)

    Example:
        >>> # In Writer module after saving manuscript
        >>> auto_commit_file(
        ...     project.git_clone_path,
        ...     'paper/01_manuscript/main.tex',
        ...     'Update manuscript introduction'
        ... )
    """
    if message is None:
        message = f"Auto-save: {filepath}"

    return git_commit_and_push(
        project_dir=project_dir,
        message=message,
        files=[filepath],
        branch="develop",
        push=True,
    )


def init_git_repo_with_gitea_remote(
    local_dir: Path, gitea_clone_url: str, username: str, email: str
) -> bool:
    """
    Initialize a git repository and set up Gitea as remote.

    Args:
        local_dir: Path to local directory
        gitea_clone_url: Gitea clone URL
        username: Git user name
        email: Git user email

    Returns:
        True if successful
    """
    try:
        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=local_dir, capture_output=True, check=True)

        # Configure user
        subprocess.run(
            ["git", "config", "user.name", username],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "config", "user.email", email],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", gitea_clone_url],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initial commit"],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        logger.info(f"✓ Initialized git repo with Gitea remote: {local_dir}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git initialization failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize git repo: {e}")
        return False


# EOF
