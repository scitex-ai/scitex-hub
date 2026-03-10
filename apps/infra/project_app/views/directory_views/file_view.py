#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Directory Views - File View Module

Multi-mode file viewer with support for:
- View mode with syntax highlighting
- Edit mode for text files
- Raw/download mode for binary files
- Blame mode showing git authorship per line
- Markdown rendering
- Binary file detection and handling

Re-exports handlers from specialized submodules:
- file_view_utils: Common utility functions
- file_view_modes: Mode-specific handlers
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from ...models import Project
from ...services.syntax_highlighting import detect_language
from ..repository.api.permissions import check_project_read_access
from .file_view_modes import handle_blame_mode, handle_edit_mode, handle_raw_mode
from .file_view_utils import build_breadcrumbs, get_file_context, get_git_info

logger = logging.getLogger(__name__)


def project_file_view(request, username, slug, file_path):
    """
    View/Edit file contents (GitHub-style /blob/).

    Modes (via query parameter):
    - ?mode=view (default) - View with syntax highlighting
    - ?mode=edit - Edit file content
    - ?mode=raw - Serve raw file content
    - ?mode=blame - Show git blame information
    """
    from django.contrib.auth.models import User

    mode = request.GET.get("mode", "view")
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access
    if not check_project_read_access(request, project):
        messages.error(request, "You don't have permission to access this file.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Get file context
    result = get_file_context(request, username, slug, file_path)
    if result is None:
        messages.error(request, "File not found or invalid path.")
        return redirect("project_app:detail", username=username, slug=slug)

    _, _, project_path, full_file_path = result

    # Get Git info
    git_info = get_git_info(request, project, project_path, file_path)

    # File metadata
    file_name = full_file_path.name
    file_ext = full_file_path.suffix.lower()
    file_size = full_file_path.stat().st_size

    # Handle raw/download mode
    if mode in ("raw", "download"):
        return handle_raw_mode(full_file_path, file_name, file_ext, mode)

    # Handle blame mode
    if mode == "blame":
        return handle_blame_mode(
            request, username, slug, file_path, project, project_path, git_info
        )

    # Handle edit mode
    if mode == "edit":
        return handle_edit_mode(
            request, username, slug, file_path, project, full_file_path, file_name
        )

    # Handle view mode (default)
    return _handle_view_mode(
        request,
        username,
        slug,
        file_path,
        project,
        full_file_path,
        file_name,
        file_ext,
        file_size,
        git_info,
    )


def _handle_view_mode(
    request,
    username,
    slug,
    file_path,
    project,
    full_file_path,
    file_name,
    file_ext,
    file_size,
    git_info,
):
    """Handle view mode - display file with appropriate rendering."""
    MAX_DISPLAY_SIZE = 1024 * 1024  # 1MB

    try:
        if file_size > MAX_DISPLAY_SIZE:
            render_type = "binary"
            file_content = (
                f"File too large to display ({file_size:,} bytes). "
                f"Maximum size: {MAX_DISPLAY_SIZE:,} bytes."
            )
            file_html = None
            language = None
        else:
            render_type, file_content, file_html, language = _read_and_render_file(
                full_file_path, file_ext, file_name, file_size
            )

    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect("project_app:detail", username=username, slug=slug)

    breadcrumbs = build_breadcrumbs(project, username, slug, file_path)

    context = {
        "project": project,
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "file_ext": file_ext,
        "file_content": file_content,
        "file_html": file_html,
        "render_type": render_type,
        "language": language,
        "breadcrumbs": breadcrumbs,
        "can_edit": project.owner == request.user,
        "git_info": git_info,
    }

    return render(request, "project_app/repository/file_view.html", context)


def _read_and_render_file(full_file_path, file_ext, file_name, file_size):
    """Read file and determine appropriate rendering method."""
    binary_extensions = [
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
    ]

    is_binary = file_ext in binary_extensions

    if is_binary:
        if file_ext in [".png", ".jpg", ".jpeg", ".gif"]:
            return "image", None, None, None
        elif file_ext == ".pdf":
            return "pdf", None, None, None
        else:
            return "binary", f"Binary file ({file_size:,} bytes)", None, None

    # Try to read as text file
    try:
        with open(full_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        language = detect_language(file_ext, file_name)

        if file_ext == ".md":
            import markdown

            file_html = markdown.markdown(
                file_content,
                extensions=["fenced_code", "tables", "nl2br", "codehilite"],
            )
            return "markdown", file_content, file_html, language

        if language:
            return "code", file_content, None, language

        return "text", file_content, None, None

    except UnicodeDecodeError:
        return "binary", f"Binary file ({file_size:,} bytes)", None, None


# EOF
