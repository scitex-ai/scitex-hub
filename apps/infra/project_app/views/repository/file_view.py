#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/repository/file_view.py
# ----------------------------------------
"""
Repository File View

Handles file viewing functionality with syntax highlighting.
"""

from __future__ import annotations

import logging
import subprocess

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.syntax_highlighting import detect_language

from .api.permissions import check_project_read_access

logger = logging.getLogger(__name__)


def project_file_view(request, username, slug, file_path):
    """
    View/Edit file contents (GitHub-style /blob/).

    Modes (via query parameter):
    - ?mode=view (default) - View with syntax highlighting
    - ?mode=edit - Edit file content
    - ?mode=raw - Serve raw file content

    Supports:
    - Markdown (.md) - Rendered as HTML
    - Python (.py) - Syntax highlighted
    - YAML (.yaml, .yml) - Syntax highlighted
    - JSON (.json) - Syntax highlighted
    - Text files - Plain text with line numbers
    - Images - Display inline
    """
    mode = request.GET.get("mode", "view")

    # Authenticated users → render through hub workspace (except raw/download)
    if request.user.is_authenticated and mode not in ("raw", "download"):
        from apps.workspace.repo_app.views.index import build_hub_context

        project = get_object_or_404(Project, slug=slug, owner__username=username)
        context = build_hub_context(request, current_project=project)
        return render(request, "repo_app/index.html", context)
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access (includes visitor session check)
    has_access = check_project_read_access(request, project)

    if not has_access:
        if mode in ("raw", "download"):
            raise Http404("Access denied")
        messages.error(request, "You don't have permission to access this file.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Get file path
    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        if mode in ("raw", "download"):
            raise Http404("Project directory not found")
        messages.error(request, "Project directory not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    full_file_path = project_path / file_path

    # Security check
    try:
        full_file_path = full_file_path.resolve()
        if not str(full_file_path).startswith(str(project_path.resolve())):
            if mode in ("raw", "download"):
                raise Http404("Invalid file path")
            messages.error(request, "Invalid file path.")
            return redirect("project_app:detail", username=username, slug=slug)
    except Exception:
        if mode in ("raw", "download"):
            raise Http404("Invalid file path")
        messages.error(request, "Invalid file path.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Check if file exists and is a file
    if not full_file_path.exists() or not full_file_path.is_file():
        # For raw/download mode, return 404 instead of redirect (for API/iframe usage)
        if mode in ("raw", "download"):
            raise Http404("File not found")
        messages.error(request, "File not found.")
        return redirect("project_app:detail", username=username, slug=slug)

    # Get Git commit information for this file
    git_info = {}
    try:
        # Get current branch from session or repository
        from apps.infra.project_app.api_views_module.api_views import (
            get_current_branch_from_session,
        )

        current_branch = get_current_branch_from_session(request, project)
        git_info["current_branch"] = current_branch

        # Get all branches
        all_branches_result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if all_branches_result.returncode == 0:
            branches = []
            for line in all_branches_result.stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith("*"):
                    # Remove 'remotes/origin/' prefix if present
                    branch_name = line.replace("remotes/origin/", "")
                    if branch_name and branch_name not in branches:
                        branches.append(branch_name)
                elif line.startswith("*"):
                    # Current branch
                    branch_name = line[2:].strip()
                    if branch_name not in branches:
                        branches.insert(0, branch_name)
            git_info["branches"] = branches
        else:
            git_info["branches"] = [git_info["current_branch"]]

        # Get last commit info for this specific file
        commit_result = subprocess.run(
            ["git", "log", "-1", "--format=%an|%ae|%ar|%at|%s|%h|%H", "--", file_path],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if commit_result.returncode == 0 and commit_result.stdout.strip():
            parts = commit_result.stdout.strip().split("|", 6)
            git_info.update(
                {
                    "author_name": parts[0],
                    "author_email": parts[1],
                    "time_ago": parts[2],
                    "timestamp": parts[3],
                    "message": parts[4],
                    "short_hash": parts[5],
                    "full_hash": parts[6] if len(parts) > 6 else parts[5],
                }
            )
        else:
            # File might not be committed yet
            git_info.update(
                {
                    "author_name": "",
                    "author_email": "",
                    "time_ago": "Not committed",
                    "timestamp": "",
                    "message": "No commits yet",
                    "short_hash": "",
                    "full_hash": "",
                }
            )
    except Exception as e:
        logger.debug(f"Error getting git info for {file_path}: {e}")
        git_info = {
            "current_branch": "main",
            "branches": ["main"],
            "author_name": "",
            "author_email": "",
            "time_ago": "",
            "timestamp": "",
            "message": "",
            "short_hash": "",
            "full_hash": "",
        }

    # Determine file type and rendering method
    file_name = full_file_path.name
    file_ext = full_file_path.suffix.lower()
    file_size = full_file_path.stat().st_size

    # Handle raw mode - serve file directly
    if mode == "raw" or mode == "download":
        # Determine content type based on file extension
        content_type = "text/plain; charset=utf-8"
        if file_ext == ".pdf":
            content_type = "application/pdf"
        elif file_ext in [".png"]:
            content_type = "image/png"
        elif file_ext in [".jpg", ".jpeg"]:
            content_type = "image/jpeg"
        elif file_ext in [".gif"]:
            content_type = "image/gif"

        with open(full_file_path, "rb") as f:
            response = HttpResponse(f.read(), content_type=content_type)
            # For download mode, force download instead of inline display
            disposition = "attachment" if mode == "download" else "inline"
            response["Content-Disposition"] = f'{disposition}; filename="{file_name}"'
            return response

    # Handle edit mode - redirect to file_edit view
    if mode == "edit":
        # Import the edit view from the same feature module
        from .file_edit import project_file_edit

        return project_file_edit(request, username, slug, file_path)

    # Read file content
    try:
        # Check if binary file
        # File size limit: 1MB for display
        MAX_DISPLAY_SIZE = 1024 * 1024  # 1MB
        if file_size > MAX_DISPLAY_SIZE:
            render_type = "binary"
            file_content = f"File too large to display ({file_size:,} bytes). Maximum size: {MAX_DISPLAY_SIZE:,} bytes."
            file_html = None
            language = None
        else:
            # Check if file is binary by extension first
            is_binary = file_ext in [
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

            if is_binary:
                # For images, show inline
                if file_ext in [".png", ".jpg", ".jpeg", ".gif"]:
                    render_type = "image"
                    file_content = None
                    file_html = None
                    language = None
                # For PDFs, use PDF.js viewer
                elif file_ext == ".pdf":
                    render_type = "pdf"
                    file_content = None
                    file_html = None
                    language = None
                else:
                    render_type = "binary"
                    file_content = f"Binary file ({file_size:,} bytes)"
                    file_html = None
                    language = None
            else:
                # Try to read as text file
                try:
                    with open(full_file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()

                    # Detect language for syntax highlighting
                    language = detect_language(file_ext, file_name)

                    # Render based on file type
                    if file_ext == ".md":
                        import bleach
                        import markdown
                        from bleach.css_sanitizer import CSSSanitizer

                        # Render markdown to HTML
                        # Note: The 'tables' extension is enabled to render legitimate markdown tables
                        # Tables appearing inside fenced code blocks with pipe syntax are also converted
                        # to HTML tables by the markdown processor. This is expected behavior.
                        # The XSS warnings from highlight.js about unescaped HTML in code blocks are
                        # false positives - these tables are properly escaped by bleach during sanitization.
                        raw_html = markdown.markdown(
                            file_content,
                            extensions=[
                                "fenced_code",
                                "tables",
                                "nl2br",
                                "codehilite",
                            ],
                        )

                        # Sanitize HTML to prevent XSS
                        # Allow common safe tags and attributes
                        allowed_tags = bleach.ALLOWED_TAGS | {
                            "h1",
                            "h2",
                            "h3",
                            "h4",
                            "h5",
                            "h6",
                            "p",
                            "br",
                            "hr",
                            "pre",
                            "code",
                            "span",
                            "div",
                            "table",
                            "thead",
                            "tbody",
                            "tr",
                            "th",
                            "td",
                            "ul",
                            "ol",
                            "li",
                            "dl",
                            "dt",
                            "dd",
                            "img",
                            "a",
                            "strong",
                            "em",
                            "del",
                            "ins",
                            "blockquote",
                            "details",
                            "summary",
                        }
                        allowed_attributes = {
                            "*": ["class", "id"],
                            "a": ["href", "title", "rel"],
                            "img": ["src", "alt", "title", "width", "height"],
                            "code": ["class"],
                            "pre": ["class"],
                            "span": ["class", "style"],
                            "div": ["class", "style"],
                        }
                        css_sanitizer = CSSSanitizer(
                            allowed_css_properties=["color", "background-color"]
                        )

                        file_html = bleach.clean(
                            raw_html,
                            tags=allowed_tags,
                            attributes=allowed_attributes,
                            css_sanitizer=css_sanitizer,
                            strip=False,
                        )
                        render_type = "markdown"
                    elif language:
                        # Use highlight.js on frontend
                        render_type = "code"
                        file_html = None
                    else:
                        file_html = None
                        render_type = "text"

                except UnicodeDecodeError:
                    # File is binary but wasn't caught by extension check
                    render_type = "binary"
                    file_content = f"Binary file ({file_size:,} bytes)"
                    file_html = None
                    language = None

    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect("project_app:detail", username=username, slug=slug)

    # Build breadcrumb
    breadcrumbs = [{"name": project.name, "url": f"/{username}/{slug}/"}]

    path_parts = file_path.split("/")
    current_path = ""
    for i, part in enumerate(path_parts):
        current_path += part
        if i < len(path_parts) - 1:  # Directory
            current_path += "/"
            breadcrumbs.append(
                {"name": part, "url": f"/{username}/{slug}/{current_path}"}
            )
        else:  # File
            breadcrumbs.append({"name": part, "url": None})

    context = {
        "project": project,
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "file_ext": file_ext,
        "file_content": file_content,
        "file_html": file_html,
        "render_type": render_type,
        "language": language if "language" in locals() else None,
        "breadcrumbs": breadcrumbs,
        "can_edit": project.owner == request.user,
        "git_info": git_info,
    }

    return render(request, "project_app/repository/file_view.html", context)


# EOF
