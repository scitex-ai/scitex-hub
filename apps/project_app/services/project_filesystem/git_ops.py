"""
Git Operations Manager Module

Handles Git repository cloning and integration with SSH key management.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import logging

from ...models import Project

logger = logging.getLogger(__name__)


class GitOperationsManager:
    """Manages Git-related filesystem operations."""

    def __init__(self, filesystem_manager):
        """
        Initialize GitOperationsManager.

        Args:
            filesystem_manager: Parent ProjectFilesystemManager instance
        """
        self.manager = filesystem_manager

    def clone_from_git(
        self,
        project: Project,
        git_url: str,
        use_ssh: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Clone a Git repository into the project directory.

        Args:
            project: Project instance
            git_url: Git repository URL
            use_ssh: If True and SSH key exists, use SSH for cloning

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            project_path = self.manager.get_project_root_path(project)
            if not project_path or not project_path.exists():
                return False, "Project directory not found"

            env = os.environ.copy()
            ssh_used = False

            if use_ssh:
                ssh_env = self._get_ssh_environment()
                if ssh_env:
                    env = ssh_env
                    ssh_used = True

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_clone_path = Path(temp_dir) / "repo"

                result = subprocess.run(
                    ["git", "clone", git_url, str(temp_clone_path)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env,
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    return False, error_msg

                # Remove existing files
                for item in project_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)

                # Move cloned contents
                for item in temp_clone_path.iterdir():
                    dest = project_path / item.name
                    if item.is_file():
                        shutil.copy2(item, dest)
                    elif item.is_dir():
                        shutil.copytree(item, dest)

            if ssh_used:
                self._mark_ssh_key_used()

            return True, None

        except subprocess.TimeoutExpired:
            return False, "Git clone operation timed out (max 5 minutes)"
        except FileNotFoundError:
            return False, "Git command not found. Please ensure Git is installed."
        except Exception as e:
            logger.error(f"Error cloning from git: {e}")
            return False, str(e)

    def _get_ssh_environment(self) -> Optional[dict]:
        """Get SSH environment if SSH key is available.

        Returns:
            Environment dict with SSH setup, or None if not available
        """
        try:
            from .ssh_manager import SSHKeyManager

            ssh_manager = SSHKeyManager(self.manager.user)

            if ssh_manager.has_ssh_key():
                return ssh_manager.get_ssh_env()

            return None
        except Exception as e:
            logger.debug(f"SSH key not available: {e}")
            return None

    def _mark_ssh_key_used(self):
        """Mark the SSH key as used."""
        try:
            from .ssh_manager import SSHKeyManager

            ssh_manager = SSHKeyManager(self.manager.user)
            ssh_manager.mark_key_used()
        except Exception as e:
            logger.debug(f"Could not mark SSH key as used: {e}")
