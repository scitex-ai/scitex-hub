#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remote Project Manager - Mount Management."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from django.utils import timezone

if TYPE_CHECKING:
    from apps.project_app.models import Project

logger = logging.getLogger(__name__)


class RemoteMountMixin:
    """Mixin for mount management operations."""

    project: "Project"
    config: any
    mount_point: Path

    def ensure_mounted(self) -> Tuple[bool, Optional[str]]:
        """
        Ensure remote filesystem is mounted (mount if not already).

        Returns:
            (success, error_message)
        """
        # Health check if already mounted
        if self._is_mounted():
            try:
                self.mount_point.stat()
                self._update_last_accessed()
                logger.debug(f"Remote project {self.project.slug} already mounted")
                return True, None
            except OSError:
                # Mount is stale, remount
                logger.warning(f"Stale mount detected, remounting: {self.project.slug}")
                self.unmount()
                # Fall through to mount

        return self._mount()

    def _is_mounted(self) -> bool:
        """Check if filesystem is currently mounted."""
        if not self.mount_point.exists():
            return False

        cmd = ["mountpoint", "-q", str(self.mount_point)]
        result = subprocess.run(cmd, capture_output=True)
        is_mounted = result.returncode == 0

        # Update database state if different
        if is_mounted != self.config.is_mounted:
            self.config.is_mounted = is_mounted
            self.config.save(update_fields=["is_mounted"])

        return is_mounted

    def _mount(self) -> Tuple[bool, Optional[str]]:
        """Mount remote filesystem via SSHFS."""
        # Create mount point
        try:
            self.mount_point.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Failed to create mount point: {str(e)}"

        # Get SSH key
        ssh_key_path = self.config.remote_credential.private_key_path
        if not Path(ssh_key_path).exists():
            return False, f"SSH key not found: {ssh_key_path}"

        # SSHFS mount command
        remote_target = f"{self.config.ssh_username}@{self.config.ssh_host}:{self.config.remote_path}"

        cmd = self._build_sshfs_command(remote_target, ssh_key_path)

        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
            self._update_mount_state(remote_target)
            return True, None

        except subprocess.CalledProcessError as e:
            error_msg = f"SSHFS mount failed: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "SSH connection timeout (30 seconds)"

        except Exception as e:
            logger.error(f"Unexpected mount error: {str(e)}")
            return False, f"Mount failed: {str(e)}"

    def _build_sshfs_command(self, remote_target: str, ssh_key_path: str) -> list:
        """Build SSHFS mount command with options."""
        return [
            "sshfs",
            remote_target,
            str(self.mount_point),
            "-p",
            str(self.config.ssh_port),
            "-o",
            f"IdentityFile={ssh_key_path}",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ServerAliveInterval=15",
            "-o",
            "ServerAliveCountMax=3",
            "-o",
            "reconnect",
            "-o",
            "cache_timeout=20",
            "-o",
            "entry_timeout=20",
            "-o",
            "attr_timeout=20",
            "-o",
            "kernel_cache",
            "-o",
            "auto_cache",
            "-o",
            "direct_io",
            "-o",
            "Compression=yes",
            "-o",
            "allow_other",
            "-o",
            "default_permissions",
        ]

    def _update_mount_state(self, remote_target: str):
        """Update database after successful mount."""
        self.config.is_mounted = True
        self.config.mount_point = str(self.mount_point)
        self.config.mounted_at = timezone.now()
        self.config.last_accessed = timezone.now()
        self.config.save()
        logger.info(
            f"Mounted remote project: {self.project.owner.username}/{self.project.slug} "
            f"-> {remote_target}"
        )

    def unmount(self) -> Tuple[bool, Optional[str]]:
        """Unmount remote filesystem."""
        if not self._is_mounted():
            return True, None

        cmd = ["fusermount", "-u", str(self.mount_point)]

        try:
            subprocess.run(cmd, check=True, timeout=10, capture_output=True)
            self._update_unmount_state()
            return True, None

        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Unmount failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
            )
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            logger.error(f"Unexpected unmount error: {str(e)}")
            return False, f"Unmount failed: {str(e)}"

    def _update_unmount_state(self):
        """Update database after successful unmount."""
        self.config.is_mounted = False
        self.config.mount_point = None
        self.config.save()

        try:
            self.mount_point.rmdir()
        except OSError:
            pass  # Directory not empty or doesn't exist

        logger.info(f"Unmounted remote project: {self.project.slug}")


# EOF
