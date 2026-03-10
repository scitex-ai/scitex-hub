"""
SciTeX Cloud - Native File Handler

Main file handler class that provides a unified interface for filesystem operations.
This class aggregates functionality from other modules.
"""

from pathlib import Path
from typing import List, Dict, Tuple

from .constants import VIEWABLE_EXTENSIONS, BINARY_EXTENSIONS, IGNORE_PATTERNS
from .file_operations import get_file_info, read_file_content, write_file_content
from .directory_operations import list_directory, get_directory_stats, find_files
from .file_detection import is_text_file, quick_hash


class NativeFileHandler:
    """
    Handle native filesystem operations with zero database overhead.

    Philosophy: The filesystem IS the source of truth.
    Database only stores metadata and relationships.
    """

    # Re-export constants for backward compatibility
    VIEWABLE_EXTENSIONS = VIEWABLE_EXTENSIONS
    BINARY_EXTENSIONS = BINARY_EXTENSIONS
    IGNORE_PATTERNS = IGNORE_PATTERNS

    @staticmethod
    def get_file_info(file_path: Path) -> Dict:
        """Get comprehensive file information directly from filesystem."""
        return get_file_info(file_path)

    @staticmethod
    def list_directory(
        directory_path: Path, recursive: bool = False, include_hidden: bool = False
    ) -> List[Dict]:
        """List directory contents with metadata."""
        return list_directory(directory_path, recursive, include_hidden)

    @staticmethod
    def read_file_content(
        file_path: Path, max_size: int = 1024 * 1024
    ) -> Tuple[bool, str]:
        """Read file content directly from filesystem."""
        return read_file_content(file_path, max_size)

    @staticmethod
    def write_file_content(
        file_path: Path, content: str, create_dirs: bool = True
    ) -> Tuple[bool, str]:
        """Write content directly to filesystem."""
        return write_file_content(file_path, content, create_dirs)

    @staticmethod
    def is_text_file(file_path: Path) -> bool:
        """Determine if file is text (viewable/editable in UI)."""
        return is_text_file(file_path)

    @staticmethod
    def quick_hash(file_path: Path) -> str:
        """Calculate quick hash for change detection."""
        return quick_hash(file_path)

    @staticmethod
    def get_directory_stats(directory_path: Path) -> Dict:
        """Get statistics for a directory (size, file count, etc.)"""
        return get_directory_stats(directory_path)

    @staticmethod
    def find_files(
        directory_path: Path, pattern: str = "*", recursive: bool = True
    ) -> List[Path]:
        """Find files matching pattern."""
        return find_files(directory_path, pattern, recursive)

    @staticmethod
    def _should_ignore(path: Path) -> bool:
        """Check if path should be ignored based on patterns (deprecated, use constants.should_ignore)"""
        from .constants import should_ignore

        return should_ignore(path)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size in human-readable format (deprecated, use constants.format_size)"""
        from .constants import format_size

        return format_size(size_bytes)
