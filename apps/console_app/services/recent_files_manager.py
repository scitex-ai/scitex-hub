"""
Recent Files Manager

Tracks and returns recently modified files in a project, respecting .recentignore patterns.
"""

import logging
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from apps.project_app.models import Project

logger = logging.getLogger(__name__)


class RecentFilesManager:
    """Manages recent files tracking with .recentignore support."""

    # Default patterns to ignore
    DEFAULT_IGNORE_PATTERNS = [
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        ".git/",
        ".git/*",
        "node_modules/",
        "node_modules/*",
        ".venv/",
        ".venv/*",
        "venv/",
        "venv/*",
        "*.log",
        ".DS_Store",
        "*.swp",
        "*.swo",
        "*~",
        ".ipynb_checkpoints/",
        ".ipynb_checkpoints/*",
        "*.tmp",
        ".cache/",
        ".cache/*",
        ".pytest_cache/",
        ".pytest_cache/*",
        "*.egg-info/",
        "*.egg-info/*",
        ".mypy_cache/",
        ".mypy_cache/*",
        ".tox/",
        ".tox/*",
        "dist/",
        "dist/*",
        "build/",
        "build/*",
    ]

    def __init__(self, project: Project):
        self.project = project
        self.username = project.owner.username
        self.project_slug = project.slug

    def get_project_root(self) -> Optional[Path]:
        """Get the project root directory."""
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(self.project.owner)
        return manager.get_project_root_path(self.project)

    def load_recentignore(self) -> List[str]:
        """
        Load .recentignore patterns from project root.

        Returns:
            List of ignore patterns (defaults + custom patterns)
        """
        patterns = self.DEFAULT_IGNORE_PATTERNS.copy()

        project_root = self.get_project_root()
        if not project_root:
            return patterns

        recentignore_file = project_root / ".recentignore"
        if recentignore_file.exists():
            try:
                with open(recentignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if line and not line.startswith("#"):
                            patterns.append(line)
                logger.info(f"Loaded {len(patterns)} patterns from .recentignore")
            except Exception as e:
                logger.warning(f"Failed to load .recentignore: {e}")

        return patterns

    def should_ignore(self, file_path: Path, patterns: List[str]) -> bool:
        """
        Check if a file should be ignored based on patterns.

        Args:
            file_path: Path relative to project root
            patterns: List of ignore patterns

        Returns:
            True if file should be ignored
        """
        path_str = str(file_path)

        for pattern in patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                pattern_prefix = pattern.rstrip("/")
                # Check if path starts with this directory
                if path_str.startswith(pattern_prefix + "/") or path_str == pattern_prefix:
                    return True
            # Handle wildcard patterns
            elif "*" in pattern:
                if fnmatch.fnmatch(path_str, pattern):
                    return True
                # Also check basename
                if fnmatch.fnmatch(file_path.name, pattern):
                    return True
            # Handle exact matches
            else:
                if path_str == pattern or file_path.name == pattern:
                    return True

        return False

    def get_recent_files(
        self,
        limit: int = 50,
        max_age_hours: Optional[int] = 24,
        file_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recently modified files from the project.

        Args:
            limit: Maximum number of files to return
            max_age_hours: Only include files modified within this many hours (None = no limit)
            file_types: Filter by file extensions (e.g., ['.py', '.md'])

        Returns:
            List of file information dictionaries sorted by modification time (newest first)
        """
        project_root = self.get_project_root()
        if not project_root or not project_root.exists():
            return []

        ignore_patterns = self.load_recentignore()
        files = []

        # Calculate cutoff time if max_age_hours is specified
        cutoff_time = None
        if max_age_hours:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

        try:
            for item in project_root.rglob("*"):
                # Only process files
                if not item.is_file():
                    continue

                # Get relative path
                try:
                    rel_path = item.relative_to(project_root)
                except ValueError:
                    continue

                # Check if should be ignored
                if self.should_ignore(rel_path, ignore_patterns):
                    continue

                # Get file stats
                try:
                    stat = item.stat()
                    mtime = stat.st_mtime
                except (OSError, ValueError):
                    continue

                # Check age filter
                if cutoff_time and mtime < cutoff_time:
                    continue

                # Check file type filter
                if file_types and item.suffix.lower() not in file_types:
                    continue

                # Detect file category
                category = self._detect_file_category(item)

                files.append({
                    "name": item.name,
                    "path": str(rel_path),
                    "full_path": str(item),
                    "size": stat.st_size,
                    "modified": mtime,
                    "modified_ago": self._format_time_ago(mtime),
                    "extension": item.suffix.lower(),
                    "category": category,
                })

            # Sort by modification time (newest first)
            files.sort(key=lambda x: x["modified"], reverse=True)

            # Apply limit
            return files[:limit]

        except Exception as e:
            logger.error(f"Error getting recent files: {e}", exc_info=True)
            return []

    def _detect_file_category(self, file_path: Path) -> str:
        """Detect file category based on extension and location."""
        ext = file_path.suffix.lower()
        path_str = str(file_path).lower()

        # Code files
        if ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb"]:
            return "code"

        # Data files
        if ext in [".csv", ".json", ".xml", ".yaml", ".yml", ".parquet", ".hdf5", ".h5"]:
            return "data"

        # Images/Figures
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".eps"]:
            if "figure" in path_str or "plot" in path_str or "scitex/temp" in path_str:
                return "figure"
            return "image"

        # Documents
        if ext in [".md", ".txt", ".rst", ".tex", ".bib", ".doc", ".docx"]:
            return "document"

        # Notebooks
        if ext == ".ipynb":
            return "notebook"

        # Config
        if ext in [".toml", ".ini", ".cfg", ".conf"] or file_path.name.startswith("."):
            return "config"

        return "other"

    def _format_time_ago(self, timestamp: float) -> str:
        """Format timestamp as human-readable 'time ago' string."""
        now = datetime.now().timestamp()
        diff = now - timestamp

        if diff < 60:
            return "just now"
        elif diff < 3600:
            minutes = int(diff / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < 86400:
            hours = int(diff / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < 604800:
            days = int(diff / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            weeks = int(diff / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def get_recent_files_manager(project: Project) -> RecentFilesManager:
    """
    Factory function to get RecentFilesManager instance.

    Args:
        project: Project instance

    Returns:
        RecentFilesManager instance
    """
    return RecentFilesManager(project)
