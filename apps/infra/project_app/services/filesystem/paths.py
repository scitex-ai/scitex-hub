"""
Path utilities for project filesystem.

This module handles path resolution and directory structure management.
"""

from pathlib import Path
from typing import Optional
from django.conf import settings
from django.contrib.auth.models import User
from ...models import Project


def get_user_base_path(user: User) -> Path:
    """
    Get the base directory path for the user.

    Structure: ./data/users/{username}/proj/
    All projects go under the proj subdirectory.
    """
    return Path(settings.BASE_DIR) / "data" / "users" / user.username / "proj"


def get_project_root_path(user: User, project: Project) -> Optional[Path]:
    """Get the root directory path for a project.

    Always uses filesystem as the source of truth (data/users/{username}/{project-slug}/).
    This ensures Django always shows the actual filesystem state in real-time.
    """
    base_path = get_user_base_path(user)
    project_path = base_path / project.slug
    if project_path.exists():
        return project_path
    return None


def ensure_directory(path: Path) -> bool:
    """Ensure a directory exists, create if it doesn't."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {path}: {e}")
        return False


def get_file_extension(doc_type: str) -> str:
    """Get appropriate file extension for document type."""
    extensions = {
        "note": ".md",
        "manuscript": ".tex",
        "paper": ".tex",
        "report": ".md",
        "presentation": ".md",
        "dataset": ".csv",
        "code": ".py",
    }
    return extensions.get(doc_type, ".txt")


def get_subcategory(filename: str, category: str) -> str:
    """Determine subcategory based on file type and category."""
    extension = Path(filename).suffix.lower()

    if category == "data":
        if extension in [".csv", ".xlsx", ".json", ".xml", ".gz", ".zip"]:
            return "raw"
        elif extension in [".pkl", ".parquet", ".h5", ".npy", ".npz"]:
            return "processed"
        elif extension in [".png", ".jpg", ".jpeg", ".svg", ".pdf"]:
            return "figures"
        elif extension in [".pkl", ".joblib", ".h5", ".pt", ".pth"]:
            return "models"
        else:
            return "raw"
    elif category == "scripts":
        # Scripts go directly in scripts directory, subdirs created as needed
        return ""
    elif category == "docs":
        if extension in [".tex", ".bib"]:
            return "manuscripts"
        elif extension in [".md", ".txt", ".rst"]:
            return "notes"
        else:
            return "references"
    elif category == "results":
        if extension in [".csv", ".json", ".txt"]:
            return "outputs"
        elif extension in [".pdf", ".html"]:
            return "reports"
        else:
            return "analysis"
    elif category == "temp":
        if extension in [".log"]:
            return "logs"
        elif extension in [".tmp", ".temp"]:
            return "tmp"
        else:
            return "cache"
    elif category == "config":
        return ""

    return "misc"
