"""
File Tree Builder Service

Builds project file tree data structure.
Used by both the API view and template pre-seeding for instant tree rendering.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..services.git_status import get_git_status

logger = logging.getLogger(__name__)


def build_project_file_tree(project) -> Optional[dict]:
    """Build file tree JSON for a project.

    Returns dict with {"success": True, "treeData": [...], "gitSummary": {...}}
    matching the format expected by TreeDataLoader's sessionStorage cache,
    or None if the project directory doesn't exist.
    """
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        return None

    git_statuses_raw = get_git_status(project_path)
    git_statuses = {k.rstrip("/"): v for k, v in git_statuses_raw.items()}

    # Track untracked directories
    untracked_dirs = set()
    for file_path, status_obj in git_statuses.items():
        if status_obj.status == "??":
            untracked_dirs.add(file_path)

    # Build directory change map
    dirs_with_changes = {}
    for file_path, status_obj in git_statuses.items():
        parts = file_path.split("/")
        for i in range(len(parts) - 1):
            dir_path = "/".join(parts[: i + 1])
            if dir_path not in dirs_with_changes:
                dirs_with_changes[dir_path] = {
                    "status": "M",
                    "staged": status_obj.staged,
                }
            elif status_obj.staged:
                dirs_with_changes[dir_path]["staged"] = True

    def get_inherited_untracked_status(rel_path_str):
        for untracked_dir in untracked_dirs:
            if (
                rel_path_str.startswith(untracked_dir + "/")
                or rel_path_str == untracked_dir
            ):
                return {"status": "??", "staged": False}
        return None

    def _build_tree(path, max_depth=10, current_depth=0):
        items = []
        try:
            for item in sorted(
                path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            ):
                if item.name.startswith(".") and item.name not in [
                    ".git",
                    ".gitignore",
                    ".gitkeep",
                ]:
                    continue
                if item.name in ["__pycache__", "node_modules", ".venv", "venv"]:
                    continue

                rel_path = item.relative_to(project_path)
                rel_path_str = str(rel_path)

                git_status = None
                if rel_path_str in git_statuses:
                    status_obj = git_statuses[rel_path_str]
                    git_status = {
                        "status": status_obj.status,
                        "staged": status_obj.staged,
                    }
                elif item.is_dir() and rel_path_str in dirs_with_changes:
                    git_status = dirs_with_changes[rel_path_str]
                else:
                    git_status = get_inherited_untracked_status(rel_path_str)

                item_data = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": rel_path_str,
                    "git_status": git_status,
                }

                if item.is_dir() and current_depth < max_depth:
                    item_data["children"] = _build_tree(
                        item, max_depth, current_depth + 1
                    )

                items.append(item_data)
        except PermissionError:
            pass
        return items

    tree = _build_tree(project_path)

    # Add deleted files
    deleted_files = [
        (path, status) for path, status in git_statuses.items() if status.status == "D"
    ]

    def add_deleted_to_tree(tree_items, deleted_path, git_status_obj, parent_path=""):
        parts = deleted_path.split("/")
        if len(parts) == 1:
            file_name = parts[0]
            if not any(item["name"] == file_name for item in tree_items):
                tree_items.append(
                    {
                        "name": file_name,
                        "type": "file",
                        "path": deleted_path,
                        "git_status": {
                            "status": git_status_obj.status,
                            "staged": git_status_obj.staged,
                        },
                        "deleted": True,
                    }
                )
                tree_items.sort(
                    key=lambda x: (x["type"] != "directory", x["name"].lower())
                )
        else:
            dir_name = parts[0]
            remaining_path = "/".join(parts[1:])
            current_path = f"{parent_path}/{dir_name}" if parent_path else dir_name

            dir_item = None
            for item in tree_items:
                if item["name"] == dir_name and item["type"] == "directory":
                    dir_item = item
                    break

            if dir_item is None:
                dir_item = {
                    "name": dir_name,
                    "type": "directory",
                    "path": current_path,
                    "git_status": {
                        "status": "D",
                        "staged": git_status_obj.staged,
                    },
                    "children": [],
                }
                tree_items.append(dir_item)
                tree_items.sort(
                    key=lambda x: (x["type"] != "directory", x["name"].lower())
                )

            if "children" not in dir_item:
                dir_item["children"] = []

            add_deleted_to_tree(
                dir_item["children"], remaining_path, git_status_obj, current_path
            )

    for deleted_path, status in deleted_files:
        add_deleted_to_tree(tree, deleted_path, status)

    # Calculate git summary
    staged = 0
    modified = 0
    untracked = 0
    for _path, status_obj in git_statuses.items():
        if status_obj.staged:
            staged += 1
        elif status_obj.status == "??":
            untracked += 1
        else:
            modified += 1

    return {
        "success": True,
        "treeData": tree,
        "gitSummary": {"staged": staged, "modified": modified, "untracked": untracked},
    }
