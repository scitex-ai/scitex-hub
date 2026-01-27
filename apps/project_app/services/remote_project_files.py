#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remote Project Manager - File Operations (CRUD)."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from apps.project_app.models import Project

logger = logging.getLogger(__name__)


class RemoteFilesMixin:
    """Mixin for file operations on remote projects."""

    project: "Project"
    config: any
    mount_point: Path

    def ensure_mounted(self) -> Tuple[bool, Optional[str]]:
        """Abstract method - implemented by RemoteMountMixin."""
        raise NotImplementedError

    def unmount(self) -> Tuple[bool, Optional[str]]:
        """Abstract method - implemented by RemoteMountMixin."""
        raise NotImplementedError

    def _update_last_accessed(self):
        """Abstract method - implemented by main class."""
        raise NotImplementedError

    def read_file(
        self, relative_path: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Read a file from remote filesystem (mounts if needed).

        Args:
            relative_path: Path relative to remote_path

        Returns:
            (success, content, error_message)
        """
        success, error = self.ensure_mounted()
        if not success:
            return False, None, error

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

    def write_file(
        self, relative_path: str, content: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Write a file to remote filesystem.

        Args:
            relative_path: Path relative to remote_path
            content: File content

        Returns:
            (success, error_message)
        """
        success, error = self.ensure_mounted()
        if not success:
            return False, error

        file_path = self.mount_point / relative_path

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
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

    def list_directory(
        self, relative_path: str = "."
    ) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        List directory contents from remote filesystem.

        Args:
            relative_path: Path relative to remote_path

        Returns:
            (success, file_list, error_message)
        """
        success, error = self.ensure_mounted()
        if not success:
            return False, None, error

        dir_path = self.mount_point / relative_path

        try:
            entries = []

            for item in dir_path.iterdir():
                stat = item.stat()
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(self.mount_point)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                )

            # Sort: directories first, then alphabetically
            entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))

            self._update_last_accessed()
            return True, entries, None

        except FileNotFoundError:
            return False, None, f"Directory not found: {relative_path}"
        except PermissionError:
            return False, None, f"Permission denied: {relative_path}"
        except Exception as e:
            logger.error(f"Error listing directory {relative_path}: {str(e)}")
            return False, None, str(e)

    def read_file_with_retry(
        self, relative_path: str, max_retries: int = 3
    ) -> Tuple[bool, Optional[str], Optional[str]]:
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
                if error and (
                    "Input/output error" in error or "Transport endpoint" in error
                ):
                    logger.warning(
                        f"Mount error on attempt {attempt + 1}, remounting..."
                    )
                    self.unmount()
                    self.ensure_mounted()
                    continue

                # Other error, don't retry
                return False, None, error

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Read failed on attempt {attempt + 1}: {e}, retrying..."
                    )
                    time.sleep(1)
                    continue
                else:
                    return False, None, f"Failed after {max_retries} attempts: {str(e)}"

        return False, None, "Max retries exceeded"


# EOF
