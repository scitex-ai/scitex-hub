"""
File Operations Manager Module

Handles file storage, listing, and project structure operations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from django.utils.text import slugify
from ...models import Project

logger = logging.getLogger(__name__)


class FileOperationsManager:
    """Manages file operations for projects."""

    def __init__(self, filesystem_manager):
        """
        Initialize FileOperationsManager.

        Args:
            filesystem_manager: Parent ProjectFilesystemManager instance
        """
        self.manager = filesystem_manager

    def store_document(
        self,
        document,
        content: str,
        doc_type: str = "manuscripts"
    ) -> Tuple[bool, Optional[Path]]:
        """Store a document in the appropriate project directory."""
        try:
            if not document.project:
                file_path = (
                    self.manager.base_path / "temp" /
                    f"{document.id}_{document.title}.txt"
                )
            else:
                project_path = self.manager.get_project_root_path(document.project)
                if not project_path:
                    return False, None

                extension = self._get_file_extension(document.document_type)
                filename = f"{slugify(document.title)}{extension}"
                file_path = project_path / "documents" / doc_type / filename

            if not self.manager._ensure_directory(file_path.parent):
                return False, None

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            document.file_location = str(file_path.relative_to(self.manager.base_path))
            document.save()

            return True, file_path
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            return False, None

    def store_file(
        self,
        project: Project,
        file_content: bytes,
        filename: str,
        category: str = "data",
    ) -> Tuple[bool, Optional[Path]]:
        """Store a file in the project directory."""
        try:
            project_path = self.manager.get_project_root_path(project)
            if not project_path:
                return False, None

            subcategory = self._get_subcategory(filename, category)
            file_path = project_path / category / subcategory / filename

            if not self.manager._ensure_directory(file_path.parent):
                return False, None

            with open(file_path, "wb") as f:
                f.write(file_content)

            return True, file_path
        except Exception as e:
            logger.error(f"Error storing file: {e}")
            return False, None

    def list_project_files(
        self,
        project: Project,
        category: Optional[str] = None
    ) -> List[Dict]:
        """List files in a project directory."""
        try:
            project_path = self.manager.get_project_root_path(project)
            if not project_path or not project_path.exists():
                return []

            files = []
            search_path = project_path / category if category else project_path

            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
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
                    })

            return sorted(files, key=lambda x: x["modified"], reverse=True)
        except Exception as e:
            logger.error(f"Error listing project files: {e}")
            return []

    def get_project_structure(self, project: Project) -> Dict:
        """Get the complete directory structure for a project."""
        try:
            project_path = self.manager.get_project_root_path(project)
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
                    tree.update({
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                    })

                return tree

            return build_tree(project_path)
        except Exception as e:
            logger.error(f"Error getting project structure: {e}")
            return {}

    def _get_file_extension(self, doc_type: str) -> str:
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

    def _get_subcategory(self, filename: str, category: str) -> str:
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
