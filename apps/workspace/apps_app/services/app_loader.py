#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dynamic app loader — registers approved apps into the workspace registry."""

from __future__ import annotations

import logging

from apps.infra.workspace_app.registry import ModuleConfig, get_module, register_module

logger = logging.getLogger(__name__)


def load_single_app(app_module):
    """Register a single approved AppsModule into the workspace registry.

    Builds a ModuleConfig from the apps module metadata and project info,
    then calls register_module() to make it available in the tab bar.
    """
    if get_module(app_module.module_name):
        logger.debug(
            "[app_loader] Module '%s' already registered", app_module.module_name
        )
        return

    project = app_module.project
    label = app_module.module_name.replace("user_", "").replace("_", " ").title()
    icon = "fas fa-puzzle-piece"
    if project:
        label = project.name
        icon = _read_manifest_icon(project) or icon

    config = ModuleConfig(
        name=app_module.module_name,
        label=label,
        app_name="apps_app",  # Served via apps infrastructure
        icon_fa=icon,
        partial_template=f"apps_app/user_apps/{app_module.module_name}_partial.html",
        context_builder="apps.workspace.apps_app.services.app_context.build_user_app_context",
        order=90,  # After built-in modules
        default_enabled=False,  # User must install from app catalog
        ai_hint=app_module.short_description or "",
        license=_get_license(app_module),
    )
    register_module(config)
    logger.info("[app_loader] Loaded approved app: %s", app_module.module_name)


def load_approved_apps():
    """Load all approved apps into the workspace registry.

    Called during startup or after an approval to refresh the registry.
    """
    from apps.workspace.apps_app.models import AppsModule

    approved = AppsModule.objects.filter(
        visibility="public",
        project__isnull=False,
    ).select_related("project")

    loaded = 0
    for app_module in approved:
        if not get_module(app_module.module_name):
            load_single_app(app_module)
            loaded += 1

    if loaded:
        logger.info("[app_loader] Loaded %d approved apps into registry", loaded)


def pin_commit(app_module):
    """Pin the latest Gitea commit SHA on approval for reproducibility."""
    if not app_module.project:
        return
    try:
        from apps.infra.gitea_app.api_client import GiteaClient

        client = GiteaClient()
        owner = app_module.project.owner.username
        repo = app_module.project.slug
        commits = client.list_commits(owner, repo, limit=1)
        if commits and len(commits) > 0:
            from django.utils import timezone

            app_module.pinned_commit = commits[0].get("sha", "")[:40]
            app_module.pinned_at = timezone.now()
            app_module.save(update_fields=["pinned_commit", "pinned_at"])
            logger.info(
                "[app_loader] Pinned commit %s for %s",
                app_module.pinned_commit[:8],
                app_module.module_name,
            )
    except Exception:
        logger.exception(
            "[app_loader] Failed to pin commit for %s", app_module.module_name
        )


def load_dev_apps(app_dirs):
    """Load local dev app directories into the workspace registry.

    Each entry in *app_dirs* is a filesystem path to a directory containing
    a ``manifest.json`` file.  Used in dev settings via ``DEV_APPS``.
    """
    import json
    from pathlib import Path

    for app_dir in app_dirs:
        app_path = Path(app_dir)
        manifest = app_path / "manifest.json"
        if not manifest.is_file():
            logger.warning("[app_loader] DEV_APPS: no manifest.json in %s", app_dir)
            continue
        try:
            with open(manifest, encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name", app_path.name)
            if get_module(name):
                continue
            config = ModuleConfig(
                name=name,
                label=data.get("label", name.replace("_", " ").title()),
                app_name="apps_app",
                icon_fa=data.get("icon", "fas fa-puzzle-piece"),
                partial_template=f"apps_app/user_apps/{name}_partial.html",
                context_builder="apps.workspace.apps_app.services.app_context.build_user_app_context",
                order=90,
                default_enabled=True,
                status="wip",
                ai_hint=data.get("description", ""),
            )
            register_module(config)
            logger.info("[app_loader] Loaded dev app: %s from %s", name, app_dir)
        except Exception:
            logger.exception("[app_loader] Failed to load dev app from %s", app_dir)


def _read_manifest_icon(project):
    """Read icon from project's manifest.json, or return None."""
    import json

    from django.conf import settings

    manifest = settings.BASE_DIR / "data" / "projects" / project.slug / "manifest.json"
    try:
        with open(manifest, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("icon", "")
    except Exception:
        return None


def _get_license(app_module):
    """Derive SPDX license identifier from module or project."""
    if app_module.project and app_module.project.app_license:
        return app_module.project.app_license
    return "AGPL-3.0"


# EOF
