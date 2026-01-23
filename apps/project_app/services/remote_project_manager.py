"""
Remote Project Manager

Manages remote filesystem projects with TRAMP-like on-demand access via SSHFS.

Key Features:
- SSHFS mounting on-demand (lazy loading)
- Auto-unmount after timeout (privacy)
- No local data storage
- No Git support (prevents confusion)
"""

import subprocess
import logging
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from django.utils import timezone
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class RemoteProjectManager:
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
        if project.project_type != 'remote':
            raise ValueError(f"Project {project.slug} is not a remote project")

        if not hasattr(project, 'remote_config') or not project.remote_config:
            raise ValueError(f"Project {project.slug} has no remote configuration")

        self.project = project
        self.config = project.remote_config

        # Mount point: /tmp/scitex_remote/{user_id}/{project_slug}/
        self.mount_base = Path("/tmp/scitex_remote")
        self.mount_point = self.mount_base / str(project.owner.id) / project.slug

    # ========================================================================
    # Mount Management
    # ========================================================================

    def ensure_mounted(self) -> Tuple[bool, Optional[str]]:
        """
        Ensure remote filesystem is mounted (mount if not already).

        Returns:
            (success, error_message)
        """
        # Health check if already mounted
        if self._is_mounted():
            # Try to access mount point
            try:
                self.mount_point.stat()
                self._update_last_accessed()
                logger.debug(f"Remote project {self.project.slug} already mounted and healthy")
                return True, None
            except OSError:
                # Mount is stale, remount
                logger.warning(f"Stale mount detected, remounting: {self.project.slug}")
                self.unmount()
                # Fall through to mount

        # Mount
        return self._mount()

    def _is_mounted(self) -> bool:
        """
        Check if filesystem is currently mounted.

        Returns:
            True if mounted, False otherwise
        """
        if not self.mount_point.exists():
            return False

        # Check if mount point has FUSE filesystem
        cmd = ["mountpoint", "-q", str(self.mount_point)]
        result = subprocess.run(cmd, capture_output=True)

        is_mounted = result.returncode == 0

        # Update database state if different
        if is_mounted != self.config.is_mounted:
            self.config.is_mounted = is_mounted
            self.config.save(update_fields=['is_mounted'])

        return is_mounted

    def _mount(self) -> Tuple[bool, Optional[str]]:
        """
        Mount remote filesystem via SSHFS.

        Returns:
            (success, error_message)
        """
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

        cmd = [
            "sshfs",
            remote_target,
            str(self.mount_point),
            "-p", str(self.config.ssh_port),
            "-o", f"IdentityFile={ssh_key_path}",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "reconnect",
            "-o", "cache_timeout=20",        # Metadata cache: 20 sec
            "-o", "entry_timeout=20",        # Directory entry cache: 20 sec
            "-o", "attr_timeout=20",         # Attribute cache: 20 sec
            "-o", "kernel_cache",            # Use kernel page cache
            "-o", "auto_cache",              # Automatic cache based on mtime
            "-o", "direct_io",               # Bypass cache for writes (consistency)
            "-o", "Compression=yes",         # Compress traffic
            "-o", "allow_other",             # Allow other users (for Docker)
            "-o", "default_permissions",     # Use file permissions
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )

            # Update database
            self.config.is_mounted = True
            self.config.mount_point = str(self.mount_point)
            self.config.mounted_at = timezone.now()
            self.config.last_accessed = timezone.now()
            self.config.save()

            logger.info(
                f"✅ Mounted remote project: {self.project.owner.username}/{self.project.slug} "
                f"→ {remote_target}"
            )

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

    def unmount(self) -> Tuple[bool, Optional[str]]:
        """
        Unmount remote filesystem.

        Returns:
            (success, error_message)
        """
        if not self._is_mounted():
            return True, None

        cmd = ["fusermount", "-u", str(self.mount_point)]

        try:
            subprocess.run(cmd, check=True, timeout=10, capture_output=True)

            # Update database
            self.config.is_mounted = False
            self.config.mount_point = None
            self.config.save()

            # Remove mount point directory
            try:
                self.mount_point.rmdir()
            except OSError:
                pass  # Directory not empty or doesn't exist

            logger.info(f"✅ Unmounted remote project: {self.project.slug}")
            return True, None

        except subprocess.CalledProcessError as e:
            error_msg = f"Unmount failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            logger.error(f"Unexpected unmount error: {str(e)}")
            return False, f"Unmount failed: {str(e)}"

    # ========================================================================
    # File Operations (CRUD)
    # ========================================================================

    def read_file(self, relative_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Read a file from remote filesystem (mounts if needed).

        Args:
            relative_path: Path relative to remote_path

        Returns:
            (success, content, error_message)
        """
        # Ensure mounted
        success, error = self.ensure_mounted()
        if not success:
            return False, None, error

        # Read file
        file_path = self.mount_point / relative_path

        try:
            content = file_path.read_text()
            self._update_last_accessed()
            return True, content, None

        except FileNotFoundError:
            return False, None, f"File not found: {relative_path}"
        except PermissionError:
            return False, None, f"Permission denied: {relative_path}"
        except Exception as e:
            logger.error(f"Error reading file {relative_path}: {str(e)}")
            return False, None, str(e)

    def write_file(self, relative_path: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Write a file to remote filesystem.

        Args:
            relative_path: Path relative to remote_path
            content: File content

        Returns:
            (success, error_message)
        """
        # Ensure mounted
        success, error = self.ensure_mounted()
        if not success:
            return False, error

        file_path = self.mount_point / relative_path

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content)

            self._update_last_accessed()
            return True, None

        except PermissionError:
            return False, f"Permission denied: {relative_path}"
        except Exception as e:
            logger.error(f"Error writing file {relative_path}: {str(e)}")
            return False, str(e)

    def delete_file(self, relative_path: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a file from remote filesystem.

        Args:
            relative_path: Path relative to remote_path

        Returns:
            (success, error_message)
        """
        # Ensure mounted
        success, error = self.ensure_mounted()
        if not success:
            return False, error

        file_path = self.mount_point / relative_path

        try:
            file_path.unlink()
            self._update_last_accessed()
            return True, None

        except FileNotFoundError:
            return False, f"File not found: {relative_path}"
        except PermissionError:
            return False, f"Permission denied: {relative_path}"
        except Exception as e:
            logger.error(f"Error deleting file {relative_path}: {str(e)}")
            return False, str(e)

    def list_directory(self, relative_path: str = ".") -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        List directory contents from remote filesystem.

        Args:
            relative_path: Path relative to remote_path

        Returns:
            (success, file_list, error_message)

        Example response:
            success, entries, error = manager.list_directory('.')
            # entries = [
            #     {'name': 'README.md', 'path': 'README.md', 'type': 'file', 'size': 1234, 'modified': 1234567890},
            #     {'name': 'src', 'path': 'src', 'type': 'directory', 'size': 0, 'modified': 1234567890},
            # ]
        """
        # Ensure mounted
        success, error = self.ensure_mounted()
        if not success:
            return False, None, error

        dir_path = self.mount_point / relative_path

        try:
            entries = []

            for item in dir_path.iterdir():
                stat = item.stat()

                entries.append({
                    'name': item.name,
                    'path': str(item.relative_to(self.mount_point)),
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                })

            # Sort: directories first, then alphabetically
            entries.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))

            self._update_last_accessed()
            return True, entries, None

        except FileNotFoundError:
            return False, None, f"Directory not found: {relative_path}"
        except PermissionError:
            return False, None, f"Permission denied: {relative_path}"
        except Exception as e:
            logger.error(f"Error listing directory {relative_path}: {str(e)}")
            return False, None, str(e)

    # ========================================================================
    # Connection Testing
    # ========================================================================

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test SSH connection to remote system.

        Returns:
            (success, error_message)
        """
        ssh_key_path = self.config.remote_credential.private_key_path

        cmd = [
            "ssh",
            "-p", str(self.config.ssh_port),
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
            f"{self.config.ssh_username}@{self.config.ssh_host}",
            "echo 'OK'"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=True
            )

            # Update database
            self.config.last_test_at = timezone.now()
            self.config.last_test_success = True
            self.config.save()

            return True, None

        except subprocess.CalledProcessError as e:
            error_msg = f"SSH connection failed: {e.stderr}"

            self.config.last_test_at = timezone.now()
            self.config.last_test_success = False
            self.config.save()

            return False, error_msg

        except subprocess.TimeoutExpired:
            self.config.last_test_at = timezone.now()
            self.config.last_test_success = False
            self.config.save()

            return False, "Connection timeout"

        except Exception as e:
            logger.error(f"Unexpected test error: {str(e)}")
            return False, str(e)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _update_last_accessed(self):
        """Update last accessed timestamp."""
        self.config.last_accessed = timezone.now()
        self.config.save(update_fields=['last_accessed'])

    def read_file_with_retry(self, relative_path: str, max_retries=3) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Read file with automatic retry on network errors.

        Args:
            relative_path: Path relative to remote_path
            max_retries: Maximum number of retry attempts

        Returns:
            (success, content, error_message)
        """
        for attempt in range(max_retries):
            try:
                success, content, error = self.read_file(relative_path)

                if success:
                    return True, content, None

                # If mount issue, try remounting
                if error and ("Input/output error" in error or "Transport endpoint" in error):
                    logger.warning(f"Mount error on attempt {attempt+1}, remounting...")
                    self.unmount()
                    self.ensure_mounted()
                    continue

                # Other error, don't retry
                return False, None, error

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Read failed on attempt {attempt+1}: {e}, retrying...")
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    return False, None, f"Failed after {max_retries} attempts: {str(e)}"

        return False, None, "Max retries exceeded"
