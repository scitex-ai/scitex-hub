"""
File operations for project filesystem.

This module handles file and directory operations (copy, move, delete, create).
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from django.utils.text import slugify
from ...models import Project
from .paths import (
    get_project_root_path,
    ensure_directory,
    get_file_extension,
    get_subcategory,
)


def store_document(
    user, document, content: str, doc_type: str = "manuscripts"
) -> Tuple[bool, Optional[Path]]:
    """Store a document in the appropriate project directory."""
    try:
        from .paths import get_user_base_path

        base_path = get_user_base_path(user)

        if not document.project:
            # Store in temp if no project
            file_path = base_path / "temp" / f"{document.id}_{document.title}.txt"
        else:
            project_path = get_project_root_path(user, document.project)
            if not project_path:
                return False, None

            # Determine file extension based on document type
            extension = get_file_extension(document.document_type)
            filename = f"{slugify(document.title)}{extension}"
            file_path = project_path / "documents" / doc_type / filename

        # Ensure parent directory exists
        if not ensure_directory(file_path.parent):
            return False, None

        # Write content to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Update document model with file path
        from .paths import get_user_base_path

        base_path = get_user_base_path(user)
        document.file_location = str(file_path.relative_to(base_path))
        document.save()

        return True, file_path
    except Exception as e:
        print(f"Error storing document: {e}")
        return False, None


def store_file(
    user,
    project: Project,
    file_content: bytes,
    filename: str,
    category: str = "data",
) -> Tuple[bool, Optional[Path]]:
    """Store a file in the project directory."""
    try:
        project_path = get_project_root_path(user, project)
        if not project_path:
            return False, None

        # Determine subcategory based on file type
        subcategory = get_subcategory(filename, category)
        file_path = project_path / category / subcategory / filename

        # Ensure parent directory exists
        if not ensure_directory(file_path.parent):
            return False, None

        # Write file content
        with open(file_path, "wb") as f:
            f.write(file_content)

        return True, file_path
    except Exception as e:
        print(f"Error storing file: {e}")
        return False, None


def list_project_files(
    user, project: Project, category: Optional[str] = None
) -> List[Dict]:
    """List files in a project directory."""
    try:
        project_path = get_project_root_path(user, project)
        if not project_path or not project_path.exists():
            return []

        files = []
        search_path = project_path / category if category else project_path

        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path.relative_to(project_path)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "category": file_path.parent.parent.name
                        if file_path.parent.parent != project_path
                        else "root",
                        "subcategory": file_path.parent.name
                        if file_path.parent != project_path
                        else "",
                    }
                )

        return sorted(files, key=lambda x: x["modified"], reverse=True)
    except Exception as e:
        print(f"Error listing project files: {e}")
        return []


def get_project_structure(user, project: Project) -> Dict:
    """Get the complete directory structure for a project."""
    try:
        project_path = get_project_root_path(user, project)
        if not project_path or not project_path.exists():
            return {}

        def build_tree(path: Path) -> Dict:
            tree = {
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "path": str(path.relative_to(project_path)),
                "children": [],
            }

            if path.is_dir():
                for child in sorted(path.iterdir()):
                    tree["children"].append(build_tree(child))
            else:
                stat = path.stat()
                tree.update(
                    {
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

            return tree

        return build_tree(project_path)
    except Exception as e:
        print(f"Error getting project structure: {e}")
        return {}


def delete_project_directory(user, project: Project) -> bool:
    """Delete a project directory and all its contents."""
    try:
        project_path = get_project_root_path(user, project)
        if project_path and project_path.exists():
            shutil.rmtree(project_path)
        return True
    except Exception as e:
        print(f"Error deleting project directory: {e}")
        return False


def get_storage_usage(user) -> Dict:
    """Get storage usage statistics for the user."""
    try:
        from .paths import get_user_base_path

        base_path = get_user_base_path(user)

        if not base_path.exists():
            return {"total_size": 0, "project_count": 0, "file_count": 0}

        total_size = 0
        file_count = 0

        for file_path in base_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1

        # Count projects directly under base_path
        project_count = len(
            [
                p
                for p in base_path.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ]
        )

        return {
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "project_count": project_count,
            "file_count": file_count,
        }
    except Exception as e:
        print(f"Error getting storage usage: {e}")
        return {"total_size": 0, "project_count": 0, "file_count": 0}
