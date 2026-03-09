"""
SciTeX Cloud - Filesystem Utilities

Native filesystem operations for seamless local file integration.
This module provides utilities for working directly with the filesystem
without database intermediaries.

Module Structure:
    - constants: File type definitions and ignore patterns
    - file_detection: File type detection, hashing, validation
    - file_operations: File reading, writing, and basic operations
    - directory_operations: Directory listing, stats, searching
    - file_handler: Main NativeFileHandler class
    - project_scanner: ProjectFileScanner for project-wide operations
"""

# Import main classes for backward compatibility
from .file_handler import NativeFileHandler
from .project_scanner import ProjectFileScanner

# Import constants for direct access
from .constants import (
    VIEWABLE_EXTENSIONS,
    BINARY_EXTENSIONS,
    IGNORE_PATTERNS,
    format_size,
    should_ignore,
)

# Import utility functions for convenience
from .file_detection import (
    is_text_file,
    is_binary_file,
    quick_hash,
    get_mime_type,
)

from .file_operations import (
    get_file_info,
    read_file_content,
    write_file_content,
)

from .directory_operations import (
    list_directory,
    get_directory_stats,
    find_files,
)

__all__ = [
    # Main classes
    "NativeFileHandler",
    "ProjectFileScanner",
    # Constants
    "VIEWABLE_EXTENSIONS",
    "BINARY_EXTENSIONS",
    "IGNORE_PATTERNS",
    # Utility functions
    "format_size",
    "should_ignore",
    "is_text_file",
    "is_binary_file",
    "quick_hash",
    "get_mime_type",
    "get_file_info",
    "read_file_content",
    "write_file_content",
    "list_directory",
    "get_directory_stats",
    "find_files",
]
