#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev app loader — synthesize ModuleConfig for user-installed dev apps.

Dev apps live in the source owner's project directory and are loaded
per-request (no global registry pollution). Templates are read live
from the source repo, so changes are always reflected immediately.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings

from apps.infra.workspace_app.registry import ModuleConfig

logger = logging.getLogger(__name__)


def read_manifest(project_dir: Path) -> dict:
    """Read manifest.json from a project directory with graceful defaults."""
    return resolve_manifest(project_dir)


def build_module_config(dev_install) -> ModuleConfig:
    """Synthesize a ModuleConfig from a DevInstallation record.

    This is called per-request to inject dev app tabs into the workspace.
    The config is NOT registered in the global registry.
    """
    return ModuleConfig(
        name=dev_install.module_name,
        label=dev_install.label
        or dev_install.source_repo.replace("-", " ").replace("_", " ").title(),
        app_name="apps_app",
        icon_fa=dev_install.icon,
        partial_template=f"apps_app/user_apps/{dev_install.module_name}_partial.html",
        context_builder="apps.workspace.apps_app.services.app_context.build_user_app_context",
        order=dev_install.tab_order,
        default_enabled=False,
        is_dev=True,
        status="wip",
        ai_hint=dev_install.description or "",
        url=f"/apps/{dev_install.module_name}/",
    )


def resolve_dev_project_dir(source_owner: str, source_repo: str) -> Path | None:
    """Resolve the filesystem path for a dev app's source repo."""
    return resolve_user_project_dir(
        source_owner, source_repo, base_dir=settings.BASE_DIR
    )


def resolve_dev_template(module_name: str) -> Path | None:
    """Resolve the partial template path for a dev app module.

    For module names like ``dev__<owner>__<repo>``, looks for:
    data/users/<owner>/proj/<repo>/templates/[<app_name>/]index_partial.html
    """
    parsed = parse_dev_module_name(module_name)
    if not parsed:
        return None

    owner, repo = parsed
    project_dir = resolve_dev_project_dir(owner, repo)
    if not project_dir:
        return None

    return find_partial_template(project_dir / "templates")


def validate_dev_repo(owner: str, repo: str) -> tuple[bool, str]:
    """Check if a repo exists on the filesystem and has templates/."""
    project_dir = resolve_dev_project_dir(owner, repo)
    if not project_dir:
        return False, f"Project directory not found for {owner}/{repo}"

    return validate_project_structure(project_dir)


# EOF
