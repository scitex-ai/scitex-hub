#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File Operations API - Transfer Operations (move, upload, upload_url)."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import shutil

import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .file_ops_utils import (
    ERR_EXISTS,
    ERR_INVALID_PATH,
    ERR_JSON,
    ERR_NOT_FOUND,
    get_project_context,
    git_auto_commit,
    validate_path,
)

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_file_move(request, username, slug):
    """Move a file or directory. For symlinks: recalculates relative path."""
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

        if not source_full.exists() and not source_full.is_symlink():
            return ERR_NOT_FOUND

        if dest_full.exists():
            return ERR_EXISTS

        if str(dest_full).startswith(str(source_full) + "/"):
            return JsonResponse(
                {"success": False, "error": "Cannot move into itself"}, status=400
            )

        if source_full.is_symlink():
            _move_symlink(source_full, dest_full, source_path, dest_path)
        else:
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_full), str(dest_full))

        git_auto_commit(project, project_path, dest_path, "Moved")
        return JsonResponse(
            {
                "success": True,
                "message": "Moved successfully",
                "source_path": source_path,
                "dest_path": dest_path,
            }
        )

    except json.JSONDecodeError:
        return ERR_JSON
    except Exception as e:
        logger.error(f"Error moving file: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _move_symlink(source_full, dest_full, source_path, dest_path):
    """Move symlink by recalculating relative path."""
    link_target = source_full.resolve()
    dest_full.parent.mkdir(parents=True, exist_ok=True)
    new_relative = os.path.relpath(link_target, dest_full.parent)
    source_full.unlink()
    dest_full.symlink_to(new_relative)
    logger.info(f"Moved symlink: {source_path} -> {dest_path} (target: {new_relative})")


@require_http_methods(["POST"])
def api_file_upload(request, username, slug):
    """Upload a file to the project."""
    try:
        project, project_path, error = get_project_context(request, username, slug)
        if error:
            return error

        uploaded_file = request.FILES.get("file")
        file_path = request.POST.get("path", "").strip()

        if not uploaded_file:
            return JsonResponse(
                {"success": False, "error": "No file uploaded"}, status=400
            )

        if not file_path:
            file_path = uploaded_file.name

        dest_full = validate_path(project_path, file_path)
        if not dest_full:
            return ERR_INVALID_PATH

        dest_full.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_full, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        git_auto_commit(project, project_path, file_path, "Uploaded")
        return JsonResponse(
            {
                "success": True,
                "message": "File uploaded successfully",
                "path": file_path,
                "size": uploaded_file.size,
            }
        )

    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_file_upload_url(request, username, slug):
    """Download a file from URL and save to project."""
    try:
        project, project_path, error = get_project_context(request, username, slug)
        if error:
            return error

        data = json.loads(request.body)
        url = data.get("url", "").strip()
        file_path = data.get("path", "").strip()

        if not url:
            return JsonResponse(
                {"success": False, "error": "URL is required"}, status=400
            )

        # SSRF protection: a bare requests.get on a tenant-supplied URL can reach
        # internal services (127.0.0.1 Gitea, 169.254.169.254 cloud metadata,
        # RFC1918 mgmt/DB). fetch_public_url resolves the host, rejects any
        # non-public address, and re-validates each redirect hop. Scheme is
        # checked inside it too. See apps/infra/project_app/url_safety.py.
        from apps.infra.project_app.url_safety import fetch_public_url

        try:
            resp = fetch_public_url(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SciTeX/1.0)"},
            )
            resp.raise_for_status()
        except ValueError as e:
            return JsonResponse(
                {"success": False, "error": str(e)}, status=400
            )
        except requests.RequestException as e:
            return JsonResponse(
                {"success": False, "error": f"Failed to download: {str(e)}"}, status=400
            )

        if not file_path:
            file_path = _determine_filename(url, resp)

        dest_full = validate_path(project_path, file_path)
        if not dest_full:
            return ERR_INVALID_PATH

        dest_full.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_full, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = dest_full.stat().st_size
        git_auto_commit(project, project_path, file_path, "Downloaded")

        return JsonResponse(
            {
                "success": True,
                "message": "File downloaded successfully",
                "path": file_path,
                "size": file_size,
            }
        )

    except json.JSONDecodeError:
        return ERR_JSON
    except Exception as e:
        logger.error(f"Error downloading file from URL: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _determine_filename(url, resp):
    """Determine filename from URL or response headers."""
    cd = resp.headers.get("Content-Disposition", "")
    if "filename=" in cd:
        return cd.split("filename=")[-1].strip("\"'")

    file_path = url.split("/")[-1].split("?")[0] or "download"
    if "." not in file_path:
        content_type = resp.headers.get("Content-Type", "").split(";")[0]
        ext = mimetypes.guess_extension(content_type) or ".bin"
        file_path += ext

    return file_path


# EOF
