"""
SciTeX Cloud - File Operations

Basic file operations for reading, writing, and getting file information.
"""

from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime

from .constants import format_size
from .file_detection import is_text_file, is_binary_file, quick_hash, get_mime_type


def get_file_info(file_path: Path) -> Dict:
    """
    Get comprehensive file information directly from filesystem.

    No database queries - pure filesystem operations.

    Args:
        file_path: Path to file

    Returns:
        Dictionary with file information

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    stat = file_path.stat()

    # Determine file type
    is_text = is_text_file(file_path)
    is_binary = is_binary_file(file_path)

    info = {
        "name": file_path.name,
        "path": str(file_path),
        "size": stat.st_size,
        "size_human": format_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "modified_timestamp": stat.st_mtime,
        "created": datetime.fromtimestamp(stat.st_ctime),
        "is_file": file_path.is_file(),
        "is_dir": file_path.is_dir(),
        "is_symlink": file_path.is_symlink(),
        "is_text": is_text,
        "is_binary": is_binary,
        "extension": file_path.suffix.lower(),
        "mime_type": get_mime_type(file_path),
        "permissions": oct(stat.st_mode)[-3:],
    }

    # Add quick hash for change detection (only for small text files)
    if is_text and stat.st_size < 1024 * 100:  # < 100KB
        info["content_hash"] = quick_hash(file_path)

    return info


def read_file_content(
    file_path: Path, max_size: int = 1024 * 1024
) -> Tuple[bool, str]:
    """
    Read file content directly from filesystem.

    Args:
        file_path: Path to file
        max_size: Maximum file size to read (default 1MB)

    Returns:
        Tuple of (success, content or error_message)
    """
    if not file_path.exists():
        return False, "File not found"

    if not file_path.is_file():
        return False, "Not a file"

    # Check file size
    file_size = file_path.stat().st_size
    if file_size > max_size:
        return (
            False,
            f"File too large ({format_size(file_size)}). Max size: {format_size(max_size)}",
        )

    # Check if binary
    if not is_text_file(file_path):
        return False, "Binary file - cannot display as text"

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return True, content
    except Exception as e:
        return False, f"Error reading file: {str(e)}"


def write_file_content(
    file_path: Path, content: str, create_dirs: bool = True
) -> Tuple[bool, str]:
    """
    Write content directly to filesystem.

    Args:
        file_path: Path to file
        content: Content to write
        create_dirs: Create parent directories if they don't exist

    Returns:
        Tuple of (success, message)
    """
    try:
        # Create parent directories if needed
        if create_dirs and not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        file_path.write_text(content, encoding="utf-8")

        return (
            True,
            f"File saved successfully ({format_size(len(content))})",
        )

    except PermissionError:
        return False, "Permission denied"
    except Exception as e:
        return False, f"Error writing file: {str(e)}"
