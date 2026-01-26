#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote Project Manager

Manages remote filesystem projects with TRAMP-like on-demand access via SSHFS.

Key Features:
- SSHFS mounting on-demand (lazy loading)
- Auto-unmount after timeout (privacy)
- No local data storage
- No Git support (prevents confusion)

Re-exports from specialized submodules:
- remote_project_mount: Mount management methods
- remote_project_files: File operations (CRUD)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from django.utils import timezone

from .remote_project_files import RemoteFilesMixin
from .remote_project_mount import RemoteMountMixin

logger = logging.getLogger(__name__)


class RemoteProjectManager(RemoteMountMixin, RemoteFilesMixin):
    """
    Manage remote filesystem projects with TRAMP-like on-demand access.

    Example usage:
        >>> from apps.project_app.models import Project
        >>> project = Project.objects.get(slug='my-remote-project')
        >>> manager = RemoteProjectManager(project)
        >>>
        >>> # Ensure mounted (automatic on first access)
        >>> success, error = manager.ensure_mounted()
        >>>
        >>> # Read file
        >>> success, content, error = manager.read_file('README.md')
        >>>
        >>> # Write file
        >>> success, error = manager.write_file('test.txt', 'Hello World')
        >>>
        >>> # List directory
        >>> success, entries, error = manager.list_directory('.')
        >>>
        >>> # Unmount
        >>> success, error = manager.unmount()
    """

    def __init__(self, project):
        """
        Initialize remote project manager.

        Args:
            project: Project instance (must be project_type='remote')

        Raises:
            ValueError: If project is not type 'remote'
        """
        if project.project_type != "remote":
            raise ValueError(f"Project {project.slug} is not a remote project")

        if not hasattr(project, "remote_config") or not project.remote_config:
            raise ValueError(f"Project {project.slug} has no remote configuration")

        self.project = project
        self.config = project.remote_config

        # Mount point: /tmp/scitex_remote/{user_id}/{project_slug}/
        self.mount_base = Path("/tmp/scitex_remote")
        self.mount_point = self.mount_base / str(project.owner.id) / project.slug

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test SSH connection to remote system.

        Returns:
            (success, error_message)
        """
        ssh_key_path = self.config.remote_credential.private_key_path

        cmd = [
            "ssh",
            "-p",
            str(self.config.ssh_port),
            "-i",
            ssh_key_path,
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=10",
            f"{self.config.ssh_username}@{self.config.ssh_host}",
            "echo 'OK'",
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            self._update_test_result(success=True)
            return True, None

        except subprocess.CalledProcessError as e:
            error_msg = f"SSH connection failed: {e.stderr}"
            self._update_test_result(success=False)
            return False, error_msg

        except subprocess.TimeoutExpired:
            self._update_test_result(success=False)
            return False, "Connection timeout"

        except Exception as e:
            logger.error(f"Unexpected test error: {str(e)}")
            return False, str(e)

    def _update_last_accessed(self):
        """Update last accessed timestamp."""
        self.config.last_accessed = timezone.now()
        self.config.save(update_fields=["last_accessed"])

    def _update_test_result(self, success: bool):
        """Update connection test result in database."""
        self.config.last_test_at = timezone.now()
        self.config.last_test_success = success
        self.config.save()


# EOF
