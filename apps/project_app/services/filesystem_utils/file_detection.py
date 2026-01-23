"""
SciTeX Cloud - File Detection Utilities

File type detection, hashing, and validation utilities.
"""

import hashlib
import mimetypes
from pathlib import Path

from .constants import VIEWABLE_EXTENSIONS, BINARY_EXTENSIONS


def is_text_file(file_path: Path) -> bool:
    """
    Determine if file is text (viewable/editable in UI).

    Uses heuristics:
    1. Known text extensions
    2. MIME type
    3. Content sampling (check for null bytes)

    Args:
        file_path: Path to file

    Returns:
        True if file is text
    """
    # Check extension
    if file_path.suffix.lower() in VIEWABLE_EXTENSIONS:
        return True

    # Check MIME type
    mime_type = mimetypes.guess_type(str(file_path))[0]
    if mime_type and mime_type.startswith("text/"):
        return True

    # Sample first 8KB and check for null bytes
    try:
        sample_size = min(8192, file_path.stat().st_size)
        with open(file_path, "rb") as f:
            sample = f.read(sample_size)
            # If null byte found, it's binary
            return b"\x00" not in sample
    except (OSError, IOError, ValueError):
        # File access error or invalid path, treat as binary
        return False


def is_binary_file(file_path: Path) -> bool:
    """
    Check if file is binary based on extension.

    Args:
        file_path: Path to file

    Returns:
        True if file is binary
    """
    return file_path.suffix.lower() in BINARY_EXTENSIONS


def quick_hash(file_path: Path) -> str:
    """
    Calculate quick hash for change detection.
    Uses MD5 of first/last blocks for large files.

    Args:
        file_path: Path to file

    Returns:
        MD5 hash string
    """
    hasher = hashlib.md5()
    file_size = file_path.stat().st_size

    # For small files, hash entire content
    if file_size < 1024 * 100:  # < 100KB
        hasher.update(file_path.read_bytes())
    else:
        # For large files, hash first 64KB + last 64KB
        block_size = 65536
        with open(file_path, "rb") as f:
            # First block
            hasher.update(f.read(block_size))
            # Last block
            f.seek(-min(block_size, file_size), 2)
            hasher.update(f.read())

    return hasher.hexdigest()


def get_mime_type(file_path: Path) -> str:
    """
    Get MIME type for file.

    Args:
        file_path: Path to file

    Returns:
        MIME type string or None
    """
    return mimetypes.guess_type(str(file_path))[0]
