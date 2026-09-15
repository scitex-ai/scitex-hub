#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App workspace actions: owner lookup, apply an agent edit, run privately."""

from __future__ import annotations

import logging
from pathlib import Path

from django.http import Http404

from apps.security import safe_log_field

logger = logging.getLogger(__name__)

_MAX_EDIT_BYTES = 1024 * 1024
_TREE_SKIP = {".git", "__pycache__", "node_modules", ".venv"}
_TREE_LIMIT = 200


class EditRefused(PermissionError):
    """An agent-proposed edit that must not be written."""


def owned_app_project(user, slug: str):
    """The user's own app project, or 404 — other users' apps do not exist here."""
    from apps.infra.project_app.models import Project

    project = Project.objects.filter(owner=user, slug=slug, is_app=True).first()
    if project is None:
        raise Http404("App project not found")
    return project


def project_dir_for(project) -> Path | None:
    from apps.infra.project_app.services.filesystem.paths import get_project_root_path

    return get_project_root_path(project.owner, project)


def apply_file_edit(user, project, rel_path: str, content: str) -> str:
    """Write ``content`` to ``rel_path`` inside ``project``; returns the path written.

    Refuses non-owners and any path that resolves outside the project.
    """
    from apps.infra.project_app.services.filesystem_utils.file_operations import (
        write_file_content,
    )

    from ..views.dev_project_files import _resolve_safe_path

    if not user.is_authenticated or project.owner_id != user.pk:
        raise EditRefused("Only the app's owner can edit its files")
    rel_path = (rel_path or "").strip().lstrip("/")
    if not rel_path or "\x00" in rel_path:
        raise EditRefused("A file path is required")
    if len(content.encode("utf-8")) > _MAX_EDIT_BYTES:
        raise EditRefused("Edit is too large")
    project_dir = project_dir_for(project)
    if project_dir is None:
        raise EditRefused("Project directory not found")
    target = _resolve_safe_path(project_dir, rel_path)
    if target is None or target == project_dir.resolve():
        raise EditRefused("Path is outside the project")
    if ".git" in target.relative_to(project_dir.resolve()).parts:
        raise EditRefused("Path is outside the project")
    ok, message = write_file_content(target, content)
    if not ok:
        raise EditRefused(message)
    logger.info(
        "[app_workspace] %s applied edit to %s/%s",
        user.username,
        project.slug,
        safe_log_field(rel_path),
    )
    return str(target.relative_to(project_dir.resolve()))


def list_app_files(project) -> list[str]:
    project_dir = project_dir_for(project)
    if project_dir is None:
        return []
    files: list[str] = []
    for path in sorted(project_dir.rglob("*")):
        rel = path.relative_to(project_dir)
        if any(part in _TREE_SKIP for part in rel.parts) or not path.is_file():
            continue
        files.append(str(rel))
        if len(files) >= _TREE_LIMIT:
            break
    return files


def run_privately(user, project):
    """Install the owner's app project as their private dev tab.

    Returns the DevInstallation. Only the owner may run it; the tab is visible
    to that user alone.
    """
    from ..models import DevInstallation
    from .dev_app_loader import (
        read_manifest,
        resolve_dev_project_dir,
        validate_dev_repo,
    )

    if not user.is_authenticated or project.owner_id != user.pk:
        raise PermissionError("Only the app's owner can run it privately")
    owner = project.owner.username
    is_valid, error = validate_dev_repo(owner, project.slug)
    if not is_valid:
        raise ValueError(error)
    project_dir = resolve_dev_project_dir(owner, project.slug)
    manifest = read_manifest(project_dir) if project_dir else {}
    install, created = DevInstallation.objects.get_or_create(
        user=user,
        source_owner=owner,
        source_repo=project.slug,
        defaults={
            "module_name": f"dev__{owner}__{project.slug}",
            "label": manifest.get("label", project.slug),
            "icon": manifest.get("icon", "fas fa-puzzle-piece"),
            "description": (manifest.get("description") or "")[:500],
        },
    )
    if not created and not install.is_enabled:
        install.is_enabled = True
        install.save(update_fields=["is_enabled"])
    return install


def dev_tab_url(install) -> str:
    return f"/apps/{install.module_name}/"


# EOF
