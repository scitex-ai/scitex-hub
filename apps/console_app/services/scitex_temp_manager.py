"""
SciTeX Temporary Directory Manager

Manages the scitex/temp directory for each project where temporal outputs
(like matplotlib figures, intermediate results, etc.) are stored.

Path structure: /home/username/proj/projectname/scitex/temp/
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from django.contrib.auth.models import User
from apps.project_app.models import Project

logger = logging.getLogger(__name__)


class ScitexTempManager:
    """Manages scitex/temp directory and tracks recent files for projects."""

    def __init__(self, project: Project):
        self.project = project
        self.username = project.owner.username
        self.project_slug = project.slug

    def get_temp_path(self) -> Path:
        """
        Get the scitex/temp path for this project.
        Path: /home/username/proj/projectname/scitex/temp/
        """
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(self.project.owner)
        project_root = manager.get_project_root_path(self.project)

        if not project_root:
            raise ValueError(f"Project root not found for {self.project_slug}")

        return project_root / "scitex" / "temp"

    def ensure_temp_directory(self) -> bool:
        """
        Ensure the scitex/temp directory exists for this project.
        Creates the directory structure if it doesn't exist.

        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            temp_path = self.get_temp_path()
            temp_path.mkdir(parents=True, exist_ok=True)

            # Create a .gitkeep file to ensure the directory is tracked by git
            gitkeep_file = temp_path / ".gitkeep"
            if not gitkeep_file.exists():
                gitkeep_file.touch()

            logger.info(f"Ensured scitex/temp directory exists at: {temp_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure scitex/temp directory: {e}", exc_info=True)
            return False

    def get_temp_files(self, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of files in scitex/temp directory.

        Args:
            recursive: If True, recursively scan subdirectories

        Returns:
            List of file information dictionaries containing:
            - name: filename
            - path: relative path from scitex/temp
            - size: file size in bytes
            - modified: last modified timestamp
            - type: file or directory
        """
        try:
            temp_path = self.get_temp_path()
            if not temp_path.exists():
                return []

            files = []
            pattern = "**/*" if recursive else "*"

            for item in sorted(temp_path.glob(pattern)):
                # Skip .gitkeep and hidden files
                if item.name.startswith("."):
                    continue

                rel_path = item.relative_to(temp_path)

                file_info = {
                    "name": item.name,
                    "path": str(rel_path),
                    "type": "directory" if item.is_dir() else "file",
                    "modified": item.stat().st_mtime if item.exists() else 0,
                }

                if item.is_file():
                    file_info["size"] = item.stat().st_size

                files.append(file_info)

            return files
        except Exception as e:
            logger.error(f"Failed to get temp files: {e}", exc_info=True)
            return []

    def get_tree_structure(self) -> Optional[Dict[str, Any]]:
        """
        Get hierarchical tree structure of scitex/temp directory.

        Returns:
            Dictionary representing the tree structure with children
        """
        try:
            temp_path = self.get_temp_path()
            if not temp_path.exists():
                return None

            def build_tree(path: Path) -> Dict[str, Any]:
                """Recursively build tree structure"""
                items = []

                for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    # Skip hidden files except .gitkeep
                    if item.name.startswith(".") and item.name != ".gitkeep":
                        continue

                    rel_path = item.relative_to(temp_path)

                    item_data = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": f"scitex/temp/{rel_path}",
                    }

                    if item.is_dir():
                        item_data["children"] = build_tree(item)
                    else:
                        item_data["size"] = item.stat().st_size
                        item_data["modified"] = item.stat().st_mtime

                    items.append(item_data)

                return items

            return {
                "name": "temp",
                "type": "directory",
                "path": "scitex/temp",
                "children": build_tree(temp_path)
            }
        except Exception as e:
            logger.error(f"Failed to get tree structure: {e}", exc_info=True)
            return None

    def clear_temp_directory(self, keep_recent: int = 0) -> bool:
        """
        Clear the scitex/temp directory.

        Args:
            keep_recent: Number of recent files to keep (0 = delete all)

        Returns:
            bool: True if successful
        """
        try:
            temp_path = self.get_temp_path()
            if not temp_path.exists():
                return True

            files = list(temp_path.glob("**/*"))
            files = [f for f in files if f.is_file() and not f.name.startswith(".")]

            if keep_recent > 0:
                # Sort by modification time and keep the most recent
                files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                files_to_delete = files[keep_recent:]
            else:
                files_to_delete = files

            for file_path in files_to_delete:
                file_path.unlink()

            logger.info(f"Cleared {len(files_to_delete)} files from scitex/temp")
            return True
        except Exception as e:
            logger.error(f"Failed to clear temp directory: {e}", exc_info=True)
            return False

    def get_directory_size(self) -> int:
        """
        Get total size of scitex/temp directory in bytes.

        Returns:
            int: Total size in bytes
        """
        try:
            temp_path = self.get_temp_path()
            if not temp_path.exists():
                return 0

            total_size = 0
            for item in temp_path.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    total_size += item.stat().st_size

            return total_size
        except Exception as e:
            logger.error(f"Failed to get directory size: {e}", exc_info=True)
            return 0


def get_scitex_temp_manager(project: Project) -> ScitexTempManager:
    """
    Factory function to get ScitexTempManager instance.

    Args:
        project: Project instance

    Returns:
        ScitexTempManager instance
    """
    return ScitexTempManager(project)
