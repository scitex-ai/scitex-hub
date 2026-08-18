#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub API Views — Browse & File

File browsing and file viewing endpoints for the Hub workspace pane.
Extracted from api.py for file size compliance.
"""

import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.infra.platform_app.services.paths import resolve_within
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.project_utils import get_current_project
from apps.infra.project_app.views.projects.detail_helpers import (
    get_directory_contents,
    get_readme_content,
)

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def api_browse(request):
    """
    GET /hub/api/browse/?path=scitex/
    Browse project directory within the Hub workspace pane.
    Returns rendered file browser HTML for the given path.
    """
    current_project = get_current_project(request, user=request.user)
    if not current_project:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    rel_path = request.GET.get("path", "").strip("/")
    manager = get_project_filesystem_manager(current_project.owner)
    project_root = manager.get_project_root_path(current_project)

    # Containment is settled BEFORE the filesystem is touched. The previous
    # order called .exists()/.is_dir() on the unvalidated join and only then
    # checked containment, which truthfully answered "does this path outside
    # your project exist?" for any traversal fragment.
    browse_path = resolve_within(project_root, rel_path)
    if browse_path is None:
        return JsonResponse({"success": False, "error": "Invalid path"}, status=403)

    # is_dir() is already False for a missing path, so the old
    # `not exists() or not is_dir()` pair collapses to this.
    if not browse_path.is_dir():
        return JsonResponse({"success": False, "error": "Path not found"}, status=404)

    files, dirs = get_directory_contents(browse_path)

    # Fix paths to be relative to project root (not to browse_path)
    for d in dirs:
        d["path"] = f"{rel_path}/{d['name']}" if rel_path else d["name"]
    for f in files:
        f["path"] = f"{rel_path}/{f['name']}" if rel_path else f["name"]

    _, readme_html = get_readme_content(browse_path)

    # Build breadcrumb parts
    breadcrumbs = []
    if rel_path:
        parts = Path(rel_path).parts
        for i, part in enumerate(parts):
            breadcrumbs.append(
                {
                    "name": part,
                    "path": "/".join(parts[: i + 1]),
                }
            )

    html = render_to_string(
        "repo_app/partials/browse_content.html",
        {
            "project": current_project,
            "directories": dirs,
            "files": files,
            "readme_html": readme_html,
            "breadcrumbs": breadcrumbs,
            "current_path": rel_path,
        },
        request=request,
    )

    return JsonResponse({"success": True, "html": html, "path": rel_path})


@login_required
@require_http_methods(["GET"])
def api_file_view(request):
    """
    GET /hub/api/file/?path=scitex/writer/01_manuscript/main.tex
    View file content within the Hub workspace pane.
    Returns rendered file viewer HTML for the given file path.
    """
    current_project = get_current_project(request, user=request.user)
    if not current_project:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    rel_path = request.GET.get("path", "").strip("/")
    if not rel_path:
        return JsonResponse(
            {"success": False, "error": "No file path specified"}, status=400
        )

    manager = get_project_filesystem_manager(current_project.owner)
    project_root = manager.get_project_root_path(current_project)

    # Containment first — see the note in api_browse() above. Here the leak was
    # slightly worse: .is_file() distinguished "exists and is a file" from
    # "exists and is a directory" for paths outside the project.
    full_path = resolve_within(project_root, rel_path)
    if full_path is None:
        return JsonResponse({"success": False, "error": "Invalid path"}, status=403)

    if not full_path.is_file():
        return JsonResponse({"success": False, "error": "File not found"}, status=404)

    file_name = full_path.name
    file_ext = full_path.suffix.lower()
    file_size = full_path.stat().st_size

    # Build breadcrumbs
    breadcrumbs = []
    parts = Path(rel_path).parts
    for i, part in enumerate(parts):
        breadcrumbs.append(
            {
                "name": part,
                "path": "/".join(parts[: i + 1]),
                "is_last": i == len(parts) - 1,
            }
        )

    # Read file content
    render_type, file_content, file_html, language = _read_file_for_hub(
        full_path, file_ext, file_name, file_size
    )

    html = render_to_string(
        "repo_app/partials/file_content.html",
        {
            "project": current_project,
            "file_name": file_name,
            "file_path": rel_path,
            "file_size": file_size,
            "file_ext": file_ext,
            "file_content": file_content,
            "file_html": file_html,
            "render_type": render_type,
            "language": language,
            "breadcrumbs": breadcrumbs,
        },
        request=request,
    )

    return JsonResponse({"success": True, "html": html, "path": rel_path})


def _read_file_for_hub(full_path, file_ext, file_name, file_size):
    """Read file and determine rendering. Returns (render_type, content, html, language)."""
    from apps.infra.project_app.services.syntax_highlighting import detect_language

    MAX_DISPLAY_SIZE = 1024 * 1024  # 1MB
    BINARY_EXTS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    }

    if file_size > MAX_DISPLAY_SIZE:
        return "binary", f"File too large ({file_size:,} bytes)", None, None

    if file_ext in BINARY_EXTS:
        if file_ext in {".png", ".jpg", ".jpeg", ".gif"}:
            return "image", None, None, None
        elif file_ext == ".pdf":
            return "pdf", None, None, None
        return "binary", f"Binary file ({file_size:,} bytes)", None, None

    try:
        content = full_path.read_text(encoding="utf-8")
        language = detect_language(file_ext, file_name)

        if file_ext == ".md":
            import markdown

            html = markdown.markdown(
                content,
                extensions=["fenced_code", "tables", "nl2br", "codehilite"],
            )
            return "markdown", content, html, language

        if language:
            return "code", content, None, language

        return "text", content, None, None
    except UnicodeDecodeError:
        return "binary", f"Binary file ({file_size:,} bytes)", None, None


# EOF
