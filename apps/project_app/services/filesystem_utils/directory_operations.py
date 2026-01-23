"""
SciTeX Cloud - Directory Operations

Directory listing, statistics, and searching utilities.
"""

from pathlib import Path
from typing import List, Dict

from .constants import should_ignore, format_size
from .file_operations import get_file_info


def list_directory(
    directory_path: Path, recursive: bool = False, include_hidden: bool = False
) -> List[Dict]:
    """
    List directory contents with metadata.

    Args:
        directory_path: Path to directory
        recursive: Include subdirectories
        include_hidden: Include hidden files (starting with .)

    Returns:
        List of file/directory info dictionaries

    Raises:
        NotADirectoryError: If path is not a directory
        PermissionError: If access is denied
    """
    if not directory_path.exists() or not directory_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")

    items = []

    try:
        for item in directory_path.iterdir():
            # Skip hidden files unless requested
            if not include_hidden and item.name.startswith("."):
                continue

            # Skip ignored patterns
            if should_ignore(item):
                continue

            try:
                info = get_file_info(item)
                items.append(info)

                # Recursive directory listing
                if recursive and item.is_dir():
                    sub_items = list_directory(
                        item, recursive=True, include_hidden=include_hidden
                    )
                    items.extend(sub_items)

            except (PermissionError, OSError):
                # Skip files we can't access
                continue

        # Sort: directories first, then by name
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    except PermissionError:
        raise PermissionError(f"Permission denied: {directory_path}")

    return items


def get_directory_stats(directory_path: Path) -> Dict:
    """
    Get statistics for a directory (size, file count, etc.)

    Args:
        directory_path: Path to directory

    Returns:
        Dictionary with directory statistics
    """
    total_size = 0
    file_count = 0
    dir_count = 0

    try:
        for item in directory_path.rglob("*"):
            if should_ignore(item):
                continue

            if item.is_file():
                file_count += 1
                try:
                    total_size += item.stat().st_size
                except (OSError, IOError):
                    # Unable to stat file, skip its size
                    pass
            elif item.is_dir():
                dir_count += 1
    except (OSError, IOError, PermissionError):
        # Unable to traverse directory, return partial results
        pass

    return {
        "total_size": total_size,
        "total_size_human": format_size(total_size),
        "file_count": file_count,
        "directory_count": dir_count,
        "total_items": file_count + dir_count,
    }


def find_files(
    directory_path: Path, pattern: str = "*", recursive: bool = True
) -> List[Path]:
    """
    Find files matching pattern.

    Args:
        directory_path: Directory to search
        pattern: Glob pattern (e.g., '*.py', '**/*.md')
        recursive: Search subdirectories

    Returns:
        List of matching file paths
    """
    if recursive:
        matches = list(directory_path.rglob(pattern))
    else:
        matches = list(directory_path.glob(pattern))

    # Filter out ignored files
    matches = [m for m in matches if not should_ignore(m)]

    return matches
