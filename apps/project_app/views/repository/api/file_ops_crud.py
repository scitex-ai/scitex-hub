#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File Operations API - Basic CRUD (create, delete, rename, copy)."""

from __future__ import annotations

import json
import logging
import shutil

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .file_ops_utils import (
    ERR_EXISTS,
    ERR_INVALID_PATH,
    ERR_JSON,
    ERR_NO_PATH,
    ERR_NOT_FOUND,
    get_project_context,
    git_auto_commit,
    validate_path,
)

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_file_create(request, username, slug):
    """Create a new file or directory."""
    try:
        project, project_path, error = get_project_context(request, username, slug)
        if error:
            return error

        data = json.loads(request.body)
        file_path = data.get("path", "").strip()
        item_type = data.get("type", "file")
        content = data.get("content", "")

        if not file_path:
            return ERR_NO_PATH

        full_path = validate_path(project_path, file_path)
        if not full_path:
            return ERR_INVALID_PATH

        if full_path.exists():
            return ERR_EXISTS

        full_path.parent.mkdir(parents=True, exist_ok=True)
        if item_type == "directory":
            full_path.mkdir(parents=True, exist_ok=True)
        else:
            full_path.write_text(content, encoding="utf-8")

        git_auto_commit(project, project_path, file_path, "Created")
        item_name = "Directory" if item_type == "directory" else "File"
        return JsonResponse(
            {"success": True, "message": f"{item_name} created", "path": file_path}
        )

    except json.JSONDecodeError:
        return ERR_JSON
    except Exception as e:
        logger.error(f"Error creating file: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_file_delete(request, username, slug):
    """Delete a file or directory."""
    try:
        project, project_path, error = get_project_context(request, username, slug)
        if error:
            return error

        data = json.loads(request.body)
        file_path = data.get("path", "").strip()

        if not file_path:
            return ERR_NO_PATH

        full_path = validate_path(project_path, file_path)
        if not full_path:
            return ERR_INVALID_PATH

        if not full_path.exists():
            return ERR_NOT_FOUND

        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()

        git_auto_commit(project, project_path, file_path, "Deleted")
        return JsonResponse(
            {"success": True, "message": "Deleted successfully", "path": file_path}
        )

    except json.JSONDecodeError:
        return ERR_JSON
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_file_rename(request, username, slug):
    """Rename a file or directory."""
    try:
        project, project_path, error = get_project_context(request, username, slug)
        if error:
            return error

        data = json.loads(request.body)
        old_path = data.get("old_path", "").strip()
        new_name = data.get("new_name", "").strip()

        if not old_path or not new_name:
            return JsonResponse(
                {"success": False, "error": "old_path and new_name are required"},
                status=400,
            )

        if "/" in new_name or "\\" in new_name:
            return JsonResponse(
                {"success": False, "error": "new_name cannot contain path separators"},
                status=400,
            )

        old_full_path = validate_path(project_path, old_path)
        if not old_full_path:
            return ERR_INVALID_PATH

        if not old_full_path.exists():
            return ERR_NOT_FOUND

        new_full_path = old_full_path.parent / new_name
        new_path = str(new_full_path.relative_to(project_path))

        if new_full_path.exists():
            return ERR_EXISTS

        old_full_path.rename(new_full_path)
        git_auto_commit(project, project_path, new_path, "Renamed")

        return JsonResponse(
            {
                "success": True,
                "message": "Renamed successfully",
                "old_path": old_path,
                "new_path": new_path,
            }
        )

    except json.JSONDecodeError:
        return ERR_JSON
    except Exception as e:
        logger.error(f"Error renaming file: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_file_copy(request, username, slug):
    """Copy a file or directory."""
    try:
        project, project_path, error = get_project_context(request, username, slug)
        if error:
            return error

        data = json.loads(request.body)
        source_path = data.get("source_path", "").strip()
        dest_path = data.get("dest_path", "").strip()

        if not source_path or not dest_path:
            return JsonResponse(
                {"success": False, "error": "source_path and dest_path are required"},
                status=400,
            )

        source_full = validate_path(project_path, source_path)
        dest_full = validate_path(project_path, dest_path)

        if not source_full or not dest_full:
            return ERR_INVALID_PATH

        if not source_full.exists():
            return ERR_NOT_FOUND

        if dest_full.exists():
            return ERR_EXISTS

        dest_full.parent.mkdir(parents=True, exist_ok=True)
        if source_full.is_dir():
            shutil.copytree(source_full, dest_full)
        else:
            shutil.copy2(source_full, dest_full)

        git_auto_commit(project, project_path, dest_path, "Copied")

        return JsonResponse(
            {
                "success": True,
                "message": "Copied successfully",
                "source_path": source_path,
                "dest_path": dest_path,
            }
        )

    except json.JSONDecodeError:
        return ERR_JSON
    except Exception as e:
        logger.error(f"Error copying file: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
