#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File view mode handlers.

Provides handlers for different file view modes:
- Raw/download mode
- Blame mode
- Edit mode
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .file_view_utils import build_breadcrumbs

logger = logging.getLogger(__name__)


def handle_raw_mode(full_file_path, file_name, file_ext, mode):
    """Handle raw/download mode - serve file directly."""
    _MIME_MAP = {
        # Documents
        ".pdf": "application/pdf",
        # Images
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        # Audio
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".m4a": "audio/mp4",
        ".weba": "audio/webm",
        # Video
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
    }
    content_type = _MIME_MAP.get(file_ext, "text/plain; charset=utf-8")

    with open(full_file_path, "rb") as f:
        response = HttpResponse(f.read(), content_type=content_type)
        disposition = "attachment" if mode == "download" else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{file_name}"'
        return response


def handle_blame_mode(
    request, username, slug, file_path, project, project_path, git_info
):
    """Handle blame mode - show git blame information."""
    file_name = Path(file_path).name
    blame_lines = []

    # Get git clone path for running git commands
    git_clone_path = None
    if hasattr(project, "git_clone_path") and project.git_clone_path:
        git_clone_path = Path(project.git_clone_path)
        if not git_clone_path.exists() or not (git_clone_path / ".git").exists():
            git_clone_path = None

    if not git_clone_path:
        messages.error(
            request,
            "Git repository not available for blame. "
            "Please ensure the project is cloned from Gitea.",
        )
        return redirect(
            "project_app:file_view",
            username=username,
            slug=slug,
            file_path=file_path,
        )

    try:
        blame_result = subprocess.run(
            ["git", "blame", "--porcelain", file_path],
            cwd=git_clone_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if blame_result.returncode == 0:
            blame_lines = _parse_blame_output(blame_result.stdout)
        else:
            messages.warning(
                request,
                "Unable to get blame information. File may not be tracked in git.",
            )
            return redirect(
                "project_app:file_view",
                username=username,
                slug=slug,
                file_path=file_path,
            )

    except subprocess.TimeoutExpired:
        messages.error(request, "Git blame timed out. File may be too large.")
        return redirect(
            "project_app:file_view",
            username=username,
            slug=slug,
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"Error running git blame: {e}")
        messages.error(request, f"Error getting blame information: {e}")
        return redirect(
            "project_app:file_view",
            username=username,
            slug=slug,
            file_path=file_path,
        )

    breadcrumbs = build_breadcrumbs(project, username, slug, file_path)

    context = {
        "project": project,
        "file_name": file_name,
        "file_path": file_path,
        "blame_lines": blame_lines,
        "breadcrumbs": breadcrumbs,
        "git_info": git_info,
        "can_edit": project.owner == request.user,
        "mode": "blame",
    }
    return render(request, "project_app/repository/file_blame.html", context)


def _parse_blame_output(stdout):
    """Parse porcelain format git blame output."""
    blame_lines = []
    lines = stdout.split("\n")
    i = 0
    line_number = 1

    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue

        parts = lines[i].split()
        if len(parts) < 3:
            i += 1
            continue

        commit_hash = parts[0]
        blame_info = {
            "commit_hash": commit_hash,
            "short_hash": commit_hash[:7],
            "line_number": line_number,
            "author": "",
            "author_time": "",
            "author_time_ago": "",
            "summary": "",
            "content": "",
        }

        i += 1
        while i < len(lines) and not lines[i].startswith("\t"):
            if lines[i].startswith("author "):
                blame_info["author"] = lines[i][7:]
            elif lines[i].startswith("author-time "):
                timestamp = int(lines[i][12:])
                blame_info["author_time"] = datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M"
                )
                blame_info["author_time_ago"] = _format_time_ago(timestamp)
            elif lines[i].startswith("summary "):
                blame_info["summary"] = lines[i][8:]
            i += 1

        if i < len(lines) and lines[i].startswith("\t"):
            blame_info["content"] = lines[i][1:]
            i += 1

        blame_lines.append(blame_info)
        line_number += 1

    return blame_lines


def _format_time_ago(timestamp):
    """Format timestamp as human-readable time ago string."""
    delta = datetime.now() - datetime.fromtimestamp(timestamp)
    if delta.days > 365:
        return f"{delta.days // 365}y ago"
    elif delta.days > 30:
        return f"{delta.days // 30}mo ago"
    elif delta.days > 0:
        return f"{delta.days}d ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600}h ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60}m ago"
    else:
        return "just now"


def handle_edit_mode(
    request, username, slug, file_path, project, full_file_path, file_name
):
    """Handle edit mode - show editor and save changes."""
    if not (project.owner == request.user):
        messages.error(request, "Only project owner can edit files.")
        return redirect("project_app:detail", username=username, slug=slug)

    if request.method == "POST":
        new_content = request.POST.get("content", "")
        try:
            with open(full_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            messages.success(request, f"File '{file_name}' saved successfully!")
            return redirect(
                "project_app:file_view",
                username=username,
                slug=slug,
                file_path=file_path,
            )
        except Exception as e:
            messages.error(request, f"Error saving file: {e}")

    try:
        with open(full_file_path, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect("project_app:detail", username=username, slug=slug)

    breadcrumbs = build_breadcrumbs(project, username, slug, file_path)

    context = {
        "project": project,
        "file_name": file_name,
        "file_path": file_path,
        "file_content": file_content,
        "breadcrumbs": breadcrumbs,
        "mode": "edit",
    }
    return render(request, "project_app/repository/file_edit.html", context)


# EOF
