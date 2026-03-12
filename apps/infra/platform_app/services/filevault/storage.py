"""
FileVault — thin per-app namespace layer over ProjectFilesystemManager.

Storage layout:
    {BASE_DIR}/data/users/{username}/proj/{project_slug}/apps/{app_name}/files/{path}

All heavy-lifting (path resolution, directory creation) is delegated to
ProjectFilesystemManager and its path utilities.
"""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.filesystem.manager import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.filesystem.paths import (
    ensure_directory,
    get_project_root_path,
)


class FileVaultError(Exception):
    """Raised for FileVault-specific errors."""


class FileVault:
    """Per-app namespaced file storage within a SciTeX project.

    Storage layout:
        <project_root>/apps/<app_name>/files/<path>

    Args:
        app_name: Identifier for the calling app (e.g. "figrecipe_app").
        project:  The Project instance that owns the files.
        user:     The user performing the operation (used for access
                  control and path resolution).
    """

    def __init__(self, app_name: str, project: Project, user: User) -> None:
        self.app_name = app_name
        self.project = project
        self.user = user
        self._manager = get_project_filesystem_manager(user)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _project_root(self) -> Path:
        """Return the project root, raising FileVaultError if not found."""
        root = get_project_root_path(self.user, self.project)
        if root is None:
            raise FileVaultError(
                f"Project directory not found for project '{self.project.slug}'. "
                "Ensure the project has been initialised."
            )
        return root

    def _vault_root(self) -> Path:
        """Return the vault root directory for this app, creating it if needed."""
        vault = self._project_root() / "apps" / self.app_name / "files"
        ensure_directory(vault)
        return vault

    def _resolve(self, path: str) -> Path:
        """Resolve a relative vault path to an absolute path.

        Raises FileVaultError on path traversal attempts.
        """
        vault = self._vault_root()
        resolved = (vault / path.lstrip("/")).resolve()
        try:
            resolved.relative_to(vault.resolve())
        except ValueError:
            raise FileVaultError(f"Path traversal detected: {path!r}")
        return resolved

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, path: str, content: Union[str, bytes]) -> Path:
        """Write text or binary content to *path* inside the vault.

        Args:
            path:    Relative path within the vault (e.g. "output/result.csv").
            content: Text (str) or binary (bytes) content to write.

        Returns:
            Absolute Path of the written file.
        """
        target = self._resolve(path)
        ensure_directory(target.parent)
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
        with open(target, mode, encoding=encoding) as fh:
            fh.write(content)
        return target

    def read(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """Read a file from the vault.

        Args:
            path:   Relative path within the vault.
            binary: If True, return bytes; otherwise return str.

        Returns:
            File content as str or bytes.

        Raises:
            FileVaultError: If the file does not exist.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileVaultError(f"File not found: {path!r}")
        mode = "rb" if binary else "r"
        encoding = None if binary else "utf-8"
        with open(target, mode, encoding=encoding) as fh:
            return fh.read()

    def list(
        self,
        path: str = "/",
        extensions: Optional[List[str]] = None,
    ) -> List[Dict]:
        """List files in a vault directory.

        Args:
            path:       Relative directory path within the vault (default: root).
            extensions: Optional whitelist of extensions, e.g. [".csv", ".json"].

        Returns:
            List of dicts with keys: name, path, size, modified, mimetype.
        """
        target = self._resolve(path)
        if not target.exists():
            return []

        results = []
        vault = self._vault_root().resolve()

        for item in sorted(target.iterdir()):
            if item.is_file():
                if extensions and item.suffix.lower() not in extensions:
                    continue
                stat = item.stat()
                mime, _ = mimetypes.guess_type(item.name)
                results.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(vault)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "mimetype": mime or "application/octet-stream",
                        "type": "file",
                    }
                )
            elif item.is_dir():
                results.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(vault)),
                        "size": None,
                        "modified": None,
                        "mimetype": None,
                        "type": "directory",
                    }
                )

        return results

    def delete(self, path: str) -> None:
        """Delete a file from the vault.

        Args:
            path: Relative path within the vault.

        Raises:
            FileVaultError: If the file does not exist or is a directory.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileVaultError(f"File not found: {path!r}")
        if target.is_dir():
            raise FileVaultError(f"Path is a directory, not a file: {path!r}")
        target.unlink()

    def exists(self, path: str) -> bool:
        """Return True if *path* exists within the vault."""
        try:
            return self._resolve(path).exists()
        except FileVaultError:
            return False

    def info(self, path: str) -> Dict:
        """Return metadata about a vault file.

        Returns:
            Dict with keys: size (int), modified (ISO str), mimetype (str).

        Raises:
            FileVaultError: If the file does not exist.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileVaultError(f"File not found: {path!r}")
        stat = target.stat()
        mime, _ = mimetypes.guess_type(target.name)
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mimetype": mime or "application/octet-stream",
        }

    def abs_path(self, path: str) -> Path:
        """Resolve *path* to its absolute filesystem path.

        Useful when passing a path to an external process that expects a
        real filesystem path (e.g. scitex CLI tools).

        Raises:
            FileVaultError: On path traversal.
        """
        return self._resolve(path)
