"""
TRIP File Backend — On-demand SSH file operations via paramiko SFTP.

Provides filesystem operations for TRIP projects without local data copies.
Each method opens a fresh SSH connection, performs the operation, and closes.
"""

import logging
import stat as stat_module

import paramiko

from ..models import TripProjectConfig

logger = logging.getLogger(__name__)


class TripFileBackend:
    """On-demand SSH file operations via paramiko SFTP."""

    def __init__(self, trip_config: TripProjectConfig):
        self.config = trip_config
        self.credential = trip_config.remote_credential
        self.remote_path = trip_config.remote_path

    def _connect(self) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
        """Open SSH + SFTP connection."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.credential.ssh_host,
            port=self.credential.ssh_port,
            username=self.credential.ssh_username,
            key_filename=self.credential.private_key_path,
            timeout=15,
        )
        sftp = client.open_sftp()
        return client, sftp

    def _full_path(self, rel_path: str) -> str:
        """Join remote_path with relative path, with traversal guard."""
        import posixpath

        full = posixpath.normpath(posixpath.join(self.remote_path, rel_path))
        if not full.startswith(self.remote_path):
            raise ValueError(f"Path traversal detected: {rel_path}")
        return full

    def list_dir(self, rel_path: str = "") -> list[dict]:
        """List directory contents.

        Returns list of dicts with keys: name, type, path, mtime.
        """
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            items = []
            for attr in sftp.listdir_attr(full):
                name = attr.filename
                if name.startswith(".") and name not in [
                    ".git",
                    ".gitignore",
                    ".gitkeep",
                ]:
                    continue
                if name in ["__pycache__", "node_modules", ".venv", "venv"]:
                    continue

                is_dir = stat_module.S_ISDIR(attr.st_mode)
                import posixpath

                item_path = posixpath.join(rel_path, name) if rel_path else name
                items.append(
                    {
                        "name": name,
                        "type": "directory" if is_dir else "file",
                        "path": item_path,
                        "mtime": attr.st_mtime or 0,
                    }
                )
            items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
            return items
        finally:
            sftp.close()
            client.close()

    def read_file(self, rel_path: str) -> str:
        """Read file content as UTF-8 text."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            with sftp.open(full, "r") as f:
                return f.read().decode("utf-8")
        finally:
            sftp.close()
            client.close()

    def read_file_bytes(self, rel_path: str) -> bytes:
        """Read file as raw bytes (for binary files)."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            with sftp.open(full, "rb") as f:
                return f.read()
        finally:
            sftp.close()
            client.close()

    def write_file(self, rel_path: str, content: str) -> None:
        """Write text content to file (creates parent dirs if needed)."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            self._ensure_parent_dirs(sftp, full)
            with sftp.open(full, "w") as f:
                f.write(content.encode("utf-8"))
        finally:
            sftp.close()
            client.close()

    def delete(self, rel_path: str) -> None:
        """Delete file or directory."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            try:
                attr = sftp.stat(full)
            except FileNotFoundError:
                raise FileNotFoundError(f"Not found: {rel_path}")

            if stat_module.S_ISDIR(attr.st_mode):
                self._rmtree(sftp, full)
            else:
                sftp.remove(full)
        finally:
            sftp.close()
            client.close()

    def exists(self, rel_path: str) -> bool:
        """Check if path exists on remote."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            sftp.stat(full)
            return True
        except FileNotFoundError:
            return False
        finally:
            sftp.close()
            client.close()

    def is_file(self, rel_path: str) -> bool:
        """Check if path is a file on remote."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            attr = sftp.stat(full)
            return stat_module.S_ISREG(attr.st_mode)
        except FileNotFoundError:
            return False
        finally:
            sftp.close()
            client.close()

    def build_tree(
        self, rel_path: str = "", max_depth: int = 10, depth: int = 0
    ) -> list[dict]:
        """Build recursive file tree (for sidebar)."""
        full = self._full_path(rel_path)
        client, sftp = self._connect()
        try:
            return self._build_tree_recursive(sftp, full, rel_path, max_depth, depth)
        finally:
            sftp.close()
            client.close()

    def _build_tree_recursive(
        self, sftp, full_path, rel_path, max_depth, depth
    ) -> list[dict]:
        """Recursive tree builder using existing SFTP connection."""
        items = []
        try:
            for attr in sftp.listdir_attr(full_path):
                name = attr.filename
                if name.startswith(".") and name not in [
                    ".git",
                    ".gitignore",
                    ".gitkeep",
                ]:
                    continue
                if name in ["__pycache__", "node_modules", ".venv", "venv"]:
                    continue

                is_dir = stat_module.S_ISDIR(attr.st_mode)
                import posixpath

                item_path = posixpath.join(rel_path, name) if rel_path else name
                child_full = posixpath.join(full_path, name)

                item_data = {
                    "name": name,
                    "type": "directory" if is_dir else "file",
                    "path": item_path,
                    "mtime": attr.st_mtime or 0,
                }

                if is_dir and depth < max_depth:
                    item_data["children"] = self._build_tree_recursive(
                        sftp, child_full, item_path, max_depth, depth + 1
                    )

                items.append(item_data)
        except PermissionError:
            pass
        except IOError:
            pass

        items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        return items

    def _ensure_parent_dirs(self, sftp, full_path: str) -> None:
        """Create parent directories recursively."""
        import posixpath

        parent = posixpath.dirname(full_path)
        if parent == self.remote_path or parent == "/":
            return
        try:
            sftp.stat(parent)
        except FileNotFoundError:
            self._ensure_parent_dirs(sftp, parent)
            sftp.mkdir(parent)

    def _rmtree(self, sftp, path: str) -> None:
        """Recursively remove directory."""
        for attr in sftp.listdir_attr(path):
            import posixpath

            child = posixpath.join(path, attr.filename)
            if stat_module.S_ISDIR(attr.st_mode):
                self._rmtree(sftp, child)
            else:
                sftp.remove(child)
        sftp.rmdir(path)


def get_trip_backend(project) -> TripFileBackend:
    """Get TripFileBackend for a remote project with TRIP connection mode.

    Args:
        project: Project instance with project_type="remote" and
                 remote_config.connection_mode="trip"

    Returns:
        TripFileBackend instance

    Raises:
        ValueError: If project is not a remote/TRIP project
    """
    if project.project_type == "remote":
        config = project.remote_config
        return TripFileBackend(config)
    raise ValueError(f"Not a remote project: {project.project_type}")


# EOF
