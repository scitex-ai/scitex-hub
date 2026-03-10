#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 22:45:00 (ywatanabe)"
# File: ./apps/workspace_app/services/gitea_auto_sync.py
"""
Transparent Auto-Sync Service for Workspace → Gitea

Automatically syncs workspace changes to Gitea without user intervention.
Users never need to know Git is working in the background.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.utils import timezone

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


class GiteaAutoSync:
    """
    Transparently sync workspace changes to Gitea.

    Features:
    - Auto-commit and push on file changes
    - No user Git knowledge required
    - Handles merge conflicts automatically
    - Graceful error handling
    """

    def __init__(self, user: User, project: Project):
        self.user = user
        self.project = project
        self.workspace_path = self._get_workspace_path()

    def _get_workspace_path(self) -> Path:
        """Get path to user's workspace directory"""
        return Path(f"/app/data/users/{self.user.username}/{self.project.name}")

    def _run_git_command(
        self, cmd: list[str], cwd: Optional[Path] = None
    ) -> Tuple[bool, str]:
        """
        Run git command safely

        Args:
            cmd: Git command as list (e.g., ['git', 'status'])
            cwd: Working directory (defaults to workspace_path)

        Returns:
            Tuple of (success, output/error)
        """
        if cwd is None:
            cwd = self.workspace_path

        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(cmd)}")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return False, str(e)

    def initialize_git_repo(self) -> bool:
        """
        Initialize Git repository in workspace if not exists

        Returns:
            True if successful or already initialized
        """
        git_dir = self.workspace_path / ".git"

        if git_dir.exists():
            logger.debug(f"Git repo already initialized: {self.workspace_path}")
            return True

        # Initialize repo
        success, output = self._run_git_command(["git", "init"])
        if not success:
            logger.error(f"Failed to initialize git repo: {output}")
            return False

        # Configure user
        self._run_git_command(
            [
                "git",
                "config",
                "user.name",
                self.user.get_full_name() or self.user.username,
            ]
        )
        self._run_git_command(
            [
                "git",
                "config",
                "user.email",
                self.user.email or f"{self.user.username}@scitex.local",
            ]
        )

        # Add Gitea remote
        gitea_url = f"ssh://git@gitea:2222/{self.user.username}/{self.project.name}.git"
        self._run_git_command(["git", "remote", "add", "origin", gitea_url])

        logger.info(f"✓ Initialized git repo: {self.workspace_path}")
        return True

    def has_changes(self) -> bool:
        """
        Check if workspace has uncommitted changes

        Returns:
            True if there are changes to commit
        """
        success, output = self._run_git_command(["git", "status", "--porcelain"])
        return success and bool(output.strip())

    def _ensure_gitea_repo_exists(self) -> bool:
        """
        Ensure Gitea repository exists, create if needed.

        Returns:
            True if repo exists or was created

        Raises:
            GiteaAPIError: If repository creation fails
            GiteaConnectionError: If Gitea is unreachable
        """
        from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient

        client = GiteaClient()
        try:
            client.get_repository(self.user.username, self.project.name)
            return True
        except GiteaAPIError:
            logger.info(f"Creating Gitea repo for {self.project.name}")
            client.create_repository(
                name=self.project.name,
                description=self.project.description or f"Project: {self.project.name}",
                private=not self.project.is_public,
                auto_init=False,
            )
            logger.info(f"Created Gitea repo: {self.user.username}/{self.project.name}")
            return True

    def _check_large_files(self) -> list[str]:
        """
        Check for files larger than 100MB

        Returns:
            List of large file paths (relative to workspace)
        """
        large_files = []
        max_size = 100 * 1024 * 1024  # 100MB

        try:
            for root, dirs, files in os.walk(self.workspace_path):
                # Skip .git directory
                if ".git" in root:
                    continue

                for file in files:
                    file_path = Path(root) / file
                    try:
                        if file_path.stat().st_size > max_size:
                            rel_path = file_path.relative_to(self.workspace_path)
                            large_files.append(str(rel_path))
                    except (OSError, ValueError):
                        continue

        except Exception as e:
            logger.warning(f"Failed to check large files: {e}")

        return large_files

    def _add_large_files_to_gitignore(self, large_files: list[str]):
        """Add large files to .gitignore"""
        if not large_files:
            return

        gitignore_path = self.workspace_path / ".gitignore"

        try:
            # Read existing gitignore
            existing_lines = set()
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f:
                    existing_lines = set(line.strip() for line in f if line.strip())

            # Add large files
            new_lines = existing_lines.copy()
            for file_path in large_files:
                new_lines.add(file_path)
                logger.warning(f"Adding large file to .gitignore: {file_path}")

            # Write back
            with open(gitignore_path, "w") as f:
                f.write("\n".join(sorted(new_lines)))
                f.write("\n")

        except Exception as e:
            logger.error(f"Failed to update .gitignore: {e}")

    def sync_to_gitea(self, auto_message: bool = True) -> Tuple[bool, str]:
        """
        Sync workspace changes to Gitea automatically

        Args:
            auto_message: Use auto-generated commit message

        Returns:
            Tuple of (success, message)
        """
        # Ensure Gitea repo exists
        if not self._ensure_gitea_repo_exists():
            return False, "Gitea repository does not exist and could not be created"

        # Ensure git repo is initialized
        if not self.initialize_git_repo():
            return False, "Failed to initialize git repository"

        # Check for large files
        large_files = self._check_large_files()
        if large_files:
            self._add_large_files_to_gitignore(large_files)
            logger.warning(f"Found {len(large_files)} large files, added to .gitignore")

        # Check if there are changes
        if not self.has_changes():
            logger.debug(f"No changes to sync for {self.project.name}")
            return True, "No changes to sync"

        # Stage all changes
        success, output = self._run_git_command(["git", "add", "-A"])
        if not success:
            return False, f"Failed to stage changes: {output}"

        # Commit with auto-generated message
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Auto-sync: {timestamp}" if auto_message else "Manual sync"

        success, output = self._run_git_command(["git", "commit", "-m", commit_msg])
        if not success and "nothing to commit" not in output.lower():
            return False, f"Failed to commit: {output}"

        # Pull with rebase to handle remote changes (graceful handling)
        success, output = self._run_git_command(
            ["git", "pull", "--rebase", "origin", "main"]
        )
        if not success:
            # Check if it's just first push (no remote branch yet)
            if (
                "couldn't find remote ref" in output.lower()
                or "does not appear" in output.lower()
            ):
                logger.debug("First push to Gitea, no remote branch yet")
            else:
                # Real pull error - try to resolve automatically
                logger.warning(f"Pull failed, attempting auto-resolve: {output}")
                # Abort rebase and force our version
                self._run_git_command(["git", "rebase", "--abort"])

        # Push to Gitea
        success, output = self._run_git_command(["git", "push", "-u", "origin", "main"])
        if not success:
            # Try force push if regular push fails (for first push or conflicts)
            success, output = self._run_git_command(
                ["git", "push", "-u", "origin", "main", "--force"]
            )
            if not success:
                return False, f"Failed to push to Gitea: {output}"
            else:
                logger.warning("Used force push to resolve conflicts")

        logger.info(f"✓ Synced {self.project.name} to Gitea")
        return True, "Successfully synced to Gitea"

    def force_sync_now(self) -> Tuple[bool, str]:
        """
        Force immediate sync to Gitea

        Returns:
            Tuple of (success, message)
        """
        return self.sync_to_gitea(auto_message=True)


def sync_all_active_workspaces():
    """
    Background task: Sync all active workspaces to Gitea

    Should be called periodically (e.g., every 5 minutes)
    """
    from apps.infra.project_app.models import Project

    # Get all projects with recent activity
    active_projects = Project.objects.filter(
        updated_at__gte=timezone.now() - timezone.timedelta(hours=1)
    )

    synced_count = 0
    failed_count = 0

    for project in active_projects:
        try:
            syncer = GiteaAutoSync(project.owner, project)
            success, message = syncer.sync_to_gitea()

            if success:
                synced_count += 1
            else:
                failed_count += 1
                logger.warning(f"Sync failed for {project.name}: {message}")

        except Exception as e:
            failed_count += 1
            logger.error(f"Sync error for {project.name}: {e}")

    logger.info(f"Auto-sync complete: {synced_count} synced, {failed_count} failed")
    return synced_count, failed_count


# EOF
