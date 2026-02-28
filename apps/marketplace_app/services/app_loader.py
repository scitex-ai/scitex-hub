#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dynamic app loader — registers approved marketplace apps into the workspace registry."""

from __future__ import annotations

import logging

from apps.workspace_app.registry import ModuleConfig, get_module, register_module

logger = logging.getLogger(__name__)


def load_single_app(mp_module):
    """Register a single approved MarketplaceModule into the workspace registry.

    Builds a ModuleConfig from the marketplace module metadata and project info,
    then calls register_module() to make it available in the tab bar.
    """
    if get_module(mp_module.module_name):
        logger.debug(
            "[app_loader] Module '%s' already registered", mp_module.module_name
        )
        return

    project = mp_module.project
    label = mp_module.module_name.replace("user_", "").replace("_", " ").title()
    if project:
        label = project.name

    config = ModuleConfig(
        name=mp_module.module_name,
        label=label,
        app_name="marketplace_app",  # Served via marketplace infrastructure
        icon_fa="fas fa-puzzle-piece",
        partial_template=f"marketplace_app/user_apps/{mp_module.module_name}_partial.html",
        order=90,  # After built-in modules
        default_enabled=False,  # User must install from marketplace
        ai_hint=mp_module.short_description or "",
        license=_get_license(mp_module),
    )
    register_module(config)
    logger.info("[app_loader] Loaded approved app: %s", mp_module.module_name)


def load_approved_apps():
    """Load all approved marketplace apps into the workspace registry.

    Called during startup or after an approval to refresh the registry.
    """
    from apps.marketplace_app.models import MarketplaceModule

    approved = MarketplaceModule.objects.filter(
        visibility="public",
        project__isnull=False,
    ).select_related("project")

    loaded = 0
    for mp_module in approved:
        if not get_module(mp_module.module_name):
            load_single_app(mp_module)
            loaded += 1

    if loaded:
        logger.info("[app_loader] Loaded %d approved apps into registry", loaded)


def pin_commit(mp_module):
    """Pin the latest Gitea commit SHA on approval for reproducibility."""
    if not mp_module.project:
        return
    try:
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()
        owner = mp_module.project.owner.username
        repo = mp_module.project.slug
        commits = client._request(
            "GET", f"/repos/{owner}/{repo}/commits", params={"limit": 1}
        )
        if commits and len(commits) > 0:
            from django.utils import timezone

            mp_module.pinned_commit = commits[0].get("sha", "")[:40]
            mp_module.pinned_at = timezone.now()
            mp_module.save(update_fields=["pinned_commit", "pinned_at"])
            logger.info(
                "[app_loader] Pinned commit %s for %s",
                mp_module.pinned_commit[:8],
                mp_module.module_name,
            )
    except Exception:
        logger.exception(
            "[app_loader] Failed to pin commit for %s", mp_module.module_name
        )


def _get_license(mp_module):
    """Derive SPDX license identifier from module or project."""
    if mp_module.project and mp_module.project.app_license:
        return mp_module.project.app_license
    return "AGPL-3.0"


# EOF
