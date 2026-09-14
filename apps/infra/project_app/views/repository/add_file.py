#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add-file pages behind the project "Add file" menu: new-file/ and upload/."""

from __future__ import annotations

import logging
from urllib.parse import quote

from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from ...models import Project
from .api.file_ops_utils import get_project_path, validate_path
from .api.permissions import check_project_write_access

logger = logging.getLogger(__name__)


def _writable_project(request, username, slug):
    """Return (project, project_path, error_response)."""
    owner = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=owner)
    if not check_project_write_access(request, project):
        return None, None, HttpResponseForbidden("You cannot edit this project.")
    project_path = get_project_path(project)
    if not project_path or not project_path.exists():
        return None, None, HttpResponseForbidden("Project directory not found.")
    return project, project_path, None


def _join(directory: str, name: str) -> str:
    directory = directory.strip().strip("/")
    name = name.strip().lstrip("/")
    return f"{directory}/{name}" if directory else name


def project_new_file(request, username, slug):
    """Create a file from a name + content form, then open it."""
    project, project_path, error = _writable_project(request, username, slug)
    if error:
        return error

    context = {
        "project": project,
        "directory": request.GET.get("path", ""),
        "file_name": "",
        "file_content": "",
        "error": "",
    }
    if request.method != "POST":
        return render(request, "project_app/repository/new_file.html", context)

    directory = request.POST.get("directory", "")
    name = request.POST.get("file_name", "")
    content = request.POST.get("content", "")
    context.update(directory=directory, file_name=name, file_content=content)
    rel_path = _join(directory, name)
    full_path = validate_path(project_path, rel_path) if name.strip() else None

    if full_path is None or full_path == project_path.resolve():
        context["error"] = "Enter a valid file name inside this project."
    elif full_path.exists():
        context["error"] = f"'{rel_path}' already exists."
    if context["error"]:
        return render(
            request, "project_app/repository/new_file.html", context, status=400
        )

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return redirect(f"/{username}/{slug}/blob/{quote(rel_path)}")


def project_upload_files(request, username, slug):
    """Upload one or more files into a project directory."""
    project, project_path, error = _writable_project(request, username, slug)
    if error:
        return error

    context = {
        "project": project,
        "directory": request.GET.get("path", ""),
        "error": "",
    }
    if request.method != "POST":
        return render(request, "project_app/repository/upload_files.html", context)

    directory = request.POST.get("directory", "")
    uploads = request.FILES.getlist("files")
    context["directory"] = directory
    targets = []
    for uploaded in uploads:
        rel_path = _join(directory, uploaded.name)
        full_path = validate_path(project_path, rel_path)
        if full_path is None or full_path == project_path.resolve():
            context["error"] = f"'{uploaded.name}' is not a valid file name."
            break
        targets.append((uploaded, full_path))
    if not uploads:
        context["error"] = "Choose at least one file to upload."
    if context["error"]:
        return render(
            request, "project_app/repository/upload_files.html", context, status=400
        )

    for uploaded, full_path in targets:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as fh:
            for chunk in uploaded.chunks():
                fh.write(chunk)
    logger.info("Uploaded %d file(s) to %s/%s", len(targets), username, slug)

    clean_dir = directory.strip().strip("/")
    return redirect(f"/{username}/{slug}/{quote(clean_dir) + '/' if clean_dir else ''}")


# EOF
