#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dev App Project File CRUD API

Provides scoped file access for dev apps. All paths are validated to stay
within the current project directory. No path traversal allowed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _resolve_safe_path(project_dir: Path, rel_path: str) -> Path | None:
    """
    Resolve a relative path within project_dir, rejecting traversal attempts.

    Returns None if the path escapes project_dir.
    """
    try:
        resolved = (project_dir / rel_path).resolve()
        project_dir_resolved = project_dir.resolve()
        resolved.relative_to(project_dir_resolved)  # raises ValueError if outside
        return resolved
    except (ValueError, OSError):
        return None


def _get_project_dir(request, project_slug: str) -> Path | None:
    """Get the project directory for the authenticated user."""
    from django.conf import settings

    from apps.infra.project_app.models import Project

    try:
        project = Project.objects.get(
            slug=project_slug,
            owner=request.user,
        )
    except Project.DoesNotExist:
        return None

    base = Path(settings.BASE_DIR) / "data" / "users" / request.user.username / "proj"
    candidate = base / project.slug
    if candidate.is_dir():
        return candidate
    return None


@login_required
@require_http_methods(["GET"])
def api_dev_file_read(request, owner, repo, project_slug):
    """
    GET /apps/dev/<owner>/<repo>/project/<project_slug>/files/?path=<rel_path>

    Read a file from the current project.
    """
    rel_path = request.GET.get("path", "")
    if not rel_path:
        return JsonResponse({"success": False, "error": "path required"}, status=400)

    project_dir = _get_project_dir(request, project_slug)
    if not project_dir:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    safe_path = _resolve_safe_path(project_dir, rel_path)
    if not safe_path:
        return JsonResponse({"success": False, "error": "Invalid path"}, status=400)

    if not safe_path.is_file():
        return JsonResponse({"success": False, "error": "File not found"}, status=404)

    if safe_path.stat().st_size > _MAX_FILE_SIZE:
        return JsonResponse({"success": False, "error": "File too large"}, status=413)

    try:
        content = safe_path.read_text(encoding="utf-8", errors="replace")
        return JsonResponse({"success": True, "content": content, "path": rel_path})
    except OSError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_dev_file_write(request, owner, repo, project_slug):
    """
    POST /apps/dev/<owner>/<repo>/project/<project_slug>/files/write/

    Body: {"path": "<rel_path>", "content": "<text>"}

    Write (create or overwrite) a file in the current project.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body"}, status=400
        )

    rel_path = data.get("path", "")
    content = data.get("content", "")

    if not rel_path:
        return JsonResponse({"success": False, "error": "path required"}, status=400)

    project_dir = _get_project_dir(request, project_slug)
    if not project_dir:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    safe_path = _resolve_safe_path(project_dir, rel_path)
    if not safe_path:
        return JsonResponse({"success": False, "error": "Invalid path"}, status=400)

    if len(content.encode("utf-8")) > _MAX_FILE_SIZE:
        return JsonResponse(
            {"success": False, "error": "Content too large"}, status=413
        )

    try:
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        return JsonResponse({"success": True, "path": rel_path})
    except OSError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_dev_file_delete(request, owner, repo, project_slug):
    """
    DELETE /apps/dev/<owner>/<repo>/project/<project_slug>/files/delete/?path=<rel_path>

    Delete a file from the current project.
    """
    rel_path = request.GET.get("path", "")
    if not rel_path:
        return JsonResponse({"success": False, "error": "path required"}, status=400)

    project_dir = _get_project_dir(request, project_slug)
    if not project_dir:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    safe_path = _resolve_safe_path(project_dir, rel_path)
    if not safe_path:
        return JsonResponse({"success": False, "error": "Invalid path"}, status=400)

    if not safe_path.is_file():
        return JsonResponse({"success": False, "error": "File not found"}, status=404)

    try:
        safe_path.unlink()
        return JsonResponse({"success": True, "path": rel_path})
    except OSError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_dev_file_list(request, owner, repo, project_slug):
    """
    GET /apps/dev/<owner>/<repo>/project/<project_slug>/files/list/?path=<rel_dir>

    List files in a project subdirectory (defaults to root).
    """
    rel_path = request.GET.get("path", ".")

    project_dir = _get_project_dir(request, project_slug)
    if not project_dir:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    safe_path = _resolve_safe_path(project_dir, rel_path)
    if not safe_path:
        return JsonResponse({"success": False, "error": "Invalid path"}, status=400)

    if not safe_path.is_dir():
        return JsonResponse(
            {"success": False, "error": "Directory not found"}, status=404
        )

    entries = []
    for item in sorted(safe_path.iterdir()):
        rel = str(item.relative_to(project_dir))
        entries.append(
            {
                "name": item.name,
                "path": rel,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            }
        )

    return JsonResponse({"success": True, "entries": entries, "path": rel_path})


# EOF
