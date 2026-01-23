"""
SciTeX Cloud - Filesystem Constants

File type definitions and ignore patterns for filesystem operations.
"""

# File extensions to show in UI
VIEWABLE_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".tex",
    ".bib",
    ".sh",
    ".r",
    ".R",
    ".ipynb",
    ".html",
    ".css",
    ".js",
}

# Binary files that need special handling
BINARY_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".zip",
    ".tar",
    ".gz",
    ".pkl",
    ".npy",
    ".npz",
    ".h5",
    ".hdf5",
}

# Files to ignore
IGNORE_PATTERNS = {
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
}


def format_size(size_bytes: int) -> str:
    """Format byte size in human-readable format"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def should_ignore(path) -> bool:
    """
    Check if path should be ignored based on patterns.

    Args:
        path: Path object to check

    Returns:
        True if path should be ignored
    """
    name = path.name

    # Check exact matches
    if name in IGNORE_PATTERNS:
        return True

    # Check pattern matches (simple)
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True

    return False
