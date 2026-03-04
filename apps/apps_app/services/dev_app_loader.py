#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev app loader — synthesize ModuleConfig for user-installed dev apps.

Dev apps live in the source owner's project directory and are loaded
per-request (no global registry pollution). Templates are read live
from the source repo, so changes are always reflected immediately.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings

from apps.workspace_app.registry import ModuleConfig

logger = logging.getLogger(__name__)


def read_manifest(project_dir: Path) -> dict:
    """Read manifest.json from a project directory with graceful defaults."""
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "[dev_app_loader] Failed to read manifest at %s: %s", manifest_path, e
        )
        return {}


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
        context_builder="apps.apps_app.services.app_context.build_user_app_context",
        order=dev_install.tab_order,
        default_enabled=False,
        is_dev=True,
        status="wip",
        ai_hint=dev_install.description or "",
    )


def resolve_dev_project_dir(source_owner: str, source_repo: str) -> Path | None:
    """Resolve the filesystem path for a dev app's source repo.

    Dev apps live in the source owner's project directory:
    data/users/<owner>/proj/<repo>/
    """
    project_dir = (
        settings.BASE_DIR / "data" / "users" / source_owner / "proj" / source_repo
    )
    if project_dir.is_dir():
        return project_dir
    return None


def _find_partial(templates_dir: Path) -> Path | None:
    """Find index_partial.html in templates/ or templates/<app_name>/.

    Scaffold creates templates/<app_name>/index_partial.html, so we
    check both the flat and nested locations.
    """
    # Flat: templates/index_partial.html
    flat = templates_dir / "index_partial.html"
    if flat.is_file():
        return flat

    # Nested: templates/<subdir>/index_partial.html
    if templates_dir.is_dir():
        for subdir in templates_dir.iterdir():
            if subdir.is_dir():
                nested = subdir / "index_partial.html"
                if nested.is_file():
                    return nested
    return None


def resolve_dev_template(module_name: str) -> Path | None:
    """Resolve the partial template path for a dev app module.

    For module names like ``dev__<owner>__<repo>``, looks for:
    data/users/<owner>/proj/<repo>/templates/[<app_name>/]index_partial.html
    """
    if not module_name.startswith("dev__"):
        return None

    parts = module_name.split("__", 2)
    if len(parts) != 3:
        return None

    owner, repo = parts[1], parts[2]
    project_dir = resolve_dev_project_dir(owner, repo)
    if not project_dir:
        return None

    return _find_partial(project_dir / "templates")


def validate_dev_repo(owner: str, repo: str) -> tuple[bool, str]:
    """Check if a repo exists on the filesystem and has templates/.

    Returns (is_valid, error_message).
    """
    project_dir = resolve_dev_project_dir(owner, repo)
    if not project_dir:
        return False, f"Project directory not found for {owner}/{repo}"

    templates_dir = project_dir / "templates"
    if not templates_dir.is_dir():
        return False, f"No templates/ directory in {owner}/{repo}"

    if not _find_partial(templates_dir):
        return False, f"No index_partial.html found in templates/ of {owner}/{repo}"

    return True, ""


# EOF
