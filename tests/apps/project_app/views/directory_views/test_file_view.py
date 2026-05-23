#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/project_app/views/directory_views/file_view.py"""

import pytest

# from apps.infra.project_app.views.directory_views.file_view import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/project_app/views/directory_views/file_view.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-28"
# # File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/directory_views/file_view.py
# # ----------------------------------------
# """
# Directory Views - File View Module
#
# Multi-mode file viewer with support for:
# - View mode with syntax highlighting
# - Edit mode for text files
# - Raw/download mode for binary files
# - Blame mode showing git authorship per line
# - Markdown rendering
# - Binary file detection and handling
# """
#
# from __future__ import annotations
#
# import logging
# import subprocess
# from pathlib import Path
# from datetime import datetime
#
# from django.shortcuts import render, redirect, get_object_or_404
# from django.http import HttpResponse
# from django.contrib import messages
# from django.contrib.auth.models import User
#
# from ...models import Project
# from ...services.syntax_highlighting import detect_language
# from ..repository.api.permissions import check_project_read_access
#
# logger = logging.getLogger(__name__)
#
#
# def project_file_view(request, username, slug, file_path):
#     """
#     View/Edit file contents (GitHub-style /blob/).
#
#     Modes (via query parameter):
#     - ?mode=view (default) - View with syntax highlighting
#     - ?mode=edit - Edit file content
#     - ?mode=raw - Serve raw file content
#     - ?mode=blame - Show git blame information
#
#     Supports:
#     - Markdown (.md) - Rendered as HTML
#     - Python (.py) - Syntax highlighted
#     - YAML (.yaml, .yml) - Syntax highlighted
#     - JSON (.json) - Syntax highlighted
#     - Text files - Plain text with line numbers
#     - Images - Display inline
#     """
#     mode = request.GET.get("mode", "view")
#     user = get_object_or_404(User, username=username)
#     project = get_object_or_404(Project, slug=slug, owner=user)
#
#     # Check access (includes visitor session check)
#     has_access = check_project_read_access(request, project)
#
#     if not has_access:
#         messages.error(request, "You don't have permission to access this file.")
#         return redirect("project_app:detail", username=username, slug=slug)
#
#     # Get file path
#     from apps.infra.project_app.services.project_filesystem import (
#         get_project_filesystem_manager,
#     )
#
#     manager = get_project_filesystem_manager(project.owner)
#     project_path = manager.get_project_root_path(project)
#
#     if not project_path or not project_path.exists():
#         messages.error(request, "Project directory not found.")
#         return redirect("project_app:detail", username=username, slug=slug)
#
#     full_file_path = project_path / file_path
#
#     # Security check
#     try:
#         full_file_path = full_file_path.resolve()
#         if not str(full_file_path).startswith(str(project_path.resolve())):
#             messages.error(request, "Invalid file path.")
#             return redirect("project_app:detail", username=username, slug=slug)
#     except Exception:
#         messages.error(request, "Invalid file path.")
#         return redirect("project_app:detail", username=username, slug=slug)
#
#     # Check if file exists and is a file
#     if not full_file_path.exists() or not full_file_path.is_file():
#         messages.error(request, "File not found.")
#         return redirect("project_app:detail", username=username, slug=slug)
#
#     # Get Git commit information for this file
#     git_info = {}
#     try:
#         # Get current branch from session or repository
#         from apps.infra.project_app.api_views_module.api_views import get_current_branch_from_session
#
#         current_branch = get_current_branch_from_session(request, project)
#         git_info["current_branch"] = current_branch
#
#         # Get all branches
#         all_branches_result = subprocess.run(
#             ["git", "branch", "-a"],
#             cwd=project_path,
#             capture_output=True,
#             text=True,
#             timeout=5,
#         )
#         if all_branches_result.returncode == 0:
#             branches = []
#             for line in all_branches_result.stdout.split("\n"):
#                 line = line.strip()
#                 if line and not line.startswith("*"):
#                     # Remove 'remotes/origin/' prefix if present
#                     branch_name = line.replace("remotes/origin/", "")
#                     if branch_name and branch_name not in branches:
#                         branches.append(branch_name)
#                 elif line.startswith("*"):
#                     # Current branch
#                     branch_name = line[2:].strip()
#                     if branch_name not in branches:
#                         branches.insert(0, branch_name)
#             git_info["branches"] = branches
#         else:
#             git_info["branches"] = [git_info["current_branch"]]
#
#         # Get last commit info for this specific file
#         commit_result = subprocess.run(
#             ["git", "log", "-1", "--format=%an|%ae|%ar|%at|%s|%h|%H", "--", file_path],
#             cwd=project_path,
#             capture_output=True,
#             text=True,
#             timeout=5,
#         )
#
#         if commit_result.returncode == 0 and commit_result.stdout.strip():
#             parts = commit_result.stdout.strip().split("|", 6)
#             git_info.update(
#                 {
#                     "author_name": parts[0],
#                     "author_email": parts[1],
#                     "time_ago": parts[2],
#                     "timestamp": parts[3],
#                     "message": parts[4],
#                     "short_hash": parts[5],
#                     "full_hash": parts[6] if len(parts) > 6 else parts[5],
#                 }
#             )
#         else:
#             # File might not be committed yet
#             git_info.update(
#                 {
#                     "author_name": "",
#                     "author_email": "",
#                     "time_ago": "Not committed",
#                     "timestamp": "",
#                     "message": "No commits yet",
#                     "short_hash": "",
#                     "full_hash": "",
#                 }
#             )
#     except Exception as e:
#         logger.debug(f"Error getting git info for {file_path}: {e}")
#         git_info = {
#             "current_branch": "main",
#             "branches": ["main"],
#             "author_name": "",
#             "author_email": "",
#             "time_ago": "",
#             "timestamp": "",
#             "message": "",
#             "short_hash": "",
#             "full_hash": "",
#         }
#
#     # Determine file type and rendering method
#     file_name = full_file_path.name
#     file_ext = full_file_path.suffix.lower()
#     file_size = full_file_path.stat().st_size
#
#     # Handle raw mode - serve file directly
#     if mode == "raw" or mode == "download":
#         # Determine content type based on file extension
#         content_type = "text/plain; charset=utf-8"
#         if file_ext == ".pdf":
#             content_type = "application/pdf"
#         elif file_ext in [".png"]:
#             content_type = "image/png"
#         elif file_ext in [".jpg", ".jpeg"]:
#             content_type = "image/jpeg"
#         elif file_ext in [".gif"]:
#             content_type = "image/gif"
#
#         with open(full_file_path, "rb") as f:
#             response = HttpResponse(f.read(), content_type=content_type)
#             # For download mode, force download instead of inline display
#             disposition = "attachment" if mode == "download" else "inline"
#             response["Content-Disposition"] = f'{disposition}; filename="{file_name}"'
#             return response
#
#     # Handle blame mode - show git blame information
#     if mode == "blame":
#         blame_lines = []
#
#         # Get git clone path for running git commands
#         git_clone_path = None
#         if hasattr(project, 'git_clone_path') and project.git_clone_path:
#             from pathlib import Path
#             git_clone_path = Path(project.git_clone_path)
#             if not git_clone_path.exists() or not (git_clone_path / ".git").exists():
#                 git_clone_path = None
#
#         if not git_clone_path:
#             messages.error(request, "Git repository not available for blame. Please ensure the project is cloned from Gitea.")
#             return redirect("project_app:file_view", username=username, slug=slug, file_path=file_path)
#
#         try:
#             # Run git blame with porcelain format for easier parsing
#             blame_result = subprocess.run(
#                 ["git", "blame", "--porcelain", file_path],
#                 cwd=git_clone_path,
#                 capture_output=True,
#                 text=True,
#                 timeout=10,
#             )
#
#             if blame_result.returncode == 0:
#                 # Parse porcelain format blame output
#                 lines = blame_result.stdout.split("\n")
#                 i = 0
#                 line_number = 1
#
#                 while i < len(lines):
#                     if not lines[i].strip():
#                         i += 1
#                         continue
#
#                     # First line: commit hash, original line, final line, group lines
#                     parts = lines[i].split()
#                     if len(parts) < 3:
#                         i += 1
#                         continue
#
#                     commit_hash = parts[0]
#                     blame_info = {
#                         'commit_hash': commit_hash,
#                         'short_hash': commit_hash[:7],
#                         'line_number': line_number,
#                         'author': '',
#                         'author_time': '',
#                         'author_time_ago': '',
#                         'summary': '',
#                         'content': '',
#                     }
#
#                     # Parse following lines for this commit
#                     i += 1
#                     while i < len(lines) and not lines[i].startswith('\t'):
#                         if lines[i].startswith('author '):
#                             blame_info['author'] = lines[i][7:]
#                         elif lines[i].startswith('author-time '):
#                             timestamp = int(lines[i][12:])
#                             blame_info['author_time'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
#                             # Calculate time ago
#                             delta = datetime.now() - datetime.fromtimestamp(timestamp)
#                             if delta.days > 365:
#                                 blame_info['author_time_ago'] = f"{delta.days // 365}y ago"
#                             elif delta.days > 30:
#                                 blame_info['author_time_ago'] = f"{delta.days // 30}mo ago"
#                             elif delta.days > 0:
#                                 blame_info['author_time_ago'] = f"{delta.days}d ago"
#                             elif delta.seconds > 3600:
#                                 blame_info['author_time_ago'] = f"{delta.seconds // 3600}h ago"
#                             elif delta.seconds > 60:
#                                 blame_info['author_time_ago'] = f"{delta.seconds // 60}m ago"
#                             else:
#                                 blame_info['author_time_ago'] = "just now"
#                         elif lines[i].startswith('summary '):
#                             blame_info['summary'] = lines[i][8:]
#                         i += 1
#
#                     # Next line should be the actual code content (starts with tab)
#                     if i < len(lines) and lines[i].startswith('\t'):
#                         blame_info['content'] = lines[i][1:]  # Remove leading tab
#                         i += 1
#
#                     blame_lines.append(blame_info)
#                     line_number += 1
#             else:
#                 # Git blame failed, possibly file not in git
#                 messages.warning(request, "Unable to get blame information. File may not be tracked in git.")
#                 return redirect("project_app:file_view", username=username, slug=slug, file_path=file_path)
#
#         except subprocess.TimeoutExpired:
#             messages.error(request, "Git blame timed out. File may be too large.")
#             return redirect("project_app:file_view", username=username, slug=slug, file_path=file_path)
#         except Exception as e:
#             logger.error(f"Error running git blame: {e}")
#             messages.error(request, f"Error getting blame information: {e}")
#             return redirect("project_app:file_view", username=username, slug=slug, file_path=file_path)
#
#         # Build breadcrumb
#         breadcrumbs = [{"name": project.name, "url": f"/{username}/{slug}/"}]
#         path_parts = file_path.split("/")
#         current_path = ""
#         for i, part in enumerate(path_parts):
#             current_path += part
#             if i < len(path_parts) - 1:
#                 current_path += "/"
#                 breadcrumbs.append(
#                     {"name": part, "url": f"/{username}/{slug}/{current_path}"}
#                 )
#             else:
#                 breadcrumbs.append({"name": part, "url": None})
#
#         context = {
#             "project": project,
#             "file_name": file_name,
#             "file_path": file_path,
#             "blame_lines": blame_lines,
#             "breadcrumbs": breadcrumbs,
#             "git_info": git_info,
#             "can_edit": project.owner == request.user,
#             "mode": "blame",
#         }
#         return render(request, "project_app/repository/file_blame.html", context)
#
#     # Handle edit mode - show editor
#     if mode == "edit":
#         if not (project.owner == request.user):
#             messages.error(request, "Only project owner can edit files.")
#             return redirect("project_app:detail", username=username, slug=slug)
#
#         if request.method == "POST":
#             # Save edited content
#             new_content = request.POST.get("content", "")
#             try:
#                 with open(full_file_path, "w", encoding="utf-8") as f:
#                     f.write(new_content)
#                 messages.success(request, f"File '{file_name}' saved successfully!")
#                 return redirect(
#                     "project_app:file_view",
#                     username=username,
#                     slug=slug,
#                     file_path=file_path,
#                 )
#             except Exception as e:
#                 messages.error(request, f"Error saving file: {e}")
#
#         # Read current content for editing
#         try:
#             with open(full_file_path, "r", encoding="utf-8", errors="ignore") as f:
#                 file_content = f.read()
#         except Exception as e:
#             messages.error(request, f"Error reading file: {e}")
#             return redirect("project_app:detail", username=username, slug=slug)
#
#         # Build breadcrumb
#         breadcrumbs = [{"name": project.name, "url": f"/{username}/{slug}/"}]
#         path_parts = file_path.split("/")
#         current_path = ""
#         for i, part in enumerate(path_parts):
#             current_path += part
#             if i < len(path_parts) - 1:
#                 current_path += "/"
#                 breadcrumbs.append(
#                     {"name": part, "url": f"/{username}/{slug}/{current_path}"}
#                 )
#             else:
#                 breadcrumbs.append({"name": part, "url": None})
#
#         context = {
#             "project": project,
#             "file_name": file_name,
#             "file_path": file_path,
#             "file_content": file_content,
#             "breadcrumbs": breadcrumbs,
#             "mode": "edit",
#         }
#         return render(request, "project_app/repository/file_edit.html", context)
#
#     # Read file content
#     try:
#         # Check if binary file
#         # File size limit: 1MB for display
#         MAX_DISPLAY_SIZE = 1024 * 1024  # 1MB
#         if file_size > MAX_DISPLAY_SIZE:
#             render_type = "binary"
#             file_content = f"File too large to display ({file_size:,} bytes). Maximum size: {MAX_DISPLAY_SIZE:,} bytes."
#             file_html = None
#             language = None
#         else:
#             # Check if file is binary by extension first
#             is_binary = file_ext in [
#                 ".png",
#                 ".jpg",
#                 ".jpeg",
#                 ".gif",
#                 ".pdf",
#                 ".zip",
#                 ".tar",
#                 ".gz",
#                 ".ico",
#                 ".woff",
#                 ".woff2",
#                 ".ttf",
#                 ".eot",
#             ]
#
#             if is_binary:
#                 # For images, show inline
#                 if file_ext in [".png", ".jpg", ".jpeg", ".gif"]:
#                     render_type = "image"
#                     file_content = None
#                     file_html = None
#                     language = None
#                 # For PDFs, use PDF.js viewer
#                 elif file_ext == ".pdf":
#                     render_type = "pdf"
#                     file_content = None
#                     file_html = None
#                     language = None
#                 else:
#                     render_type = "binary"
#                     file_content = f"Binary file ({file_size:,} bytes)"
#                     file_html = None
#                     language = None
#             else:
#                 # Try to read as text file
#                 try:
#                     with open(full_file_path, "r", encoding="utf-8") as f:
#                         file_content = f.read()
#
#                     # Detect language for syntax highlighting
#                     language = detect_language(file_ext, file_name)
#
#                     # Render based on file type
#                     if file_ext == ".md":
#                         import markdown
#
#                         file_html = markdown.markdown(
#                             file_content,
#                             extensions=[
#                                 "fenced_code",
#                                 "tables",
#                                 "nl2br",
#                                 "codehilite",
#                             ],
#                         )
#                         render_type = "markdown"
#                     elif language:
#                         # Use highlight.js on frontend
#                         render_type = "code"
#                         file_html = None
#                     else:
#                         file_html = None
#                         render_type = "text"
#
#                 except UnicodeDecodeError:
#                     # File is binary but wasn't caught by extension check
#                     render_type = "binary"
#                     file_content = f"Binary file ({file_size:,} bytes)"
#                     file_html = None
#                     language = None
#
#     except Exception as e:
#         messages.error(request, f"Error reading file: {e}")
#         return redirect("project_app:detail", username=username, slug=slug)
#
#     # Build breadcrumb
#     breadcrumbs = [{"name": project.name, "url": f"/{username}/{slug}/"}]
#
#     path_parts = file_path.split("/")
#     current_path = ""
#     for i, part in enumerate(path_parts):
#         current_path += part
#         if i < len(path_parts) - 1:  # Directory
#             current_path += "/"
#             breadcrumbs.append(
#                 {"name": part, "url": f"/{username}/{slug}/{current_path}"}
#             )
#         else:  # File
#             breadcrumbs.append({"name": part, "url": None})
#
#     context = {
#         "project": project,
#         "file_name": file_name,
#         "file_path": file_path,
#         "file_size": file_size,
#         "file_ext": file_ext,
#         "file_content": file_content,
#         "file_html": file_html,
#         "render_type": render_type,
#         "language": language if "language" in locals() else None,
#         "breadcrumbs": breadcrumbs,
#         "can_edit": project.owner == request.user,
#         "git_info": git_info,
#     }
#
#     return render(request, "project_app/repository/file_view.html", context)
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/project_app/views/directory_views/file_view.py
# --------------------------------------------------------------------------------
