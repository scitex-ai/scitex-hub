#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace context processors — inject module registry data into all templates.

Added to TEMPLATES["OPTIONS"]["context_processors"] in settings.
"""

from __future__ import annotations

import logging

from .registry import extract_module_from_path, get_all_modules, is_workspace_path

logger = logging.getLogger(__name__)


def workspace_context(request):
    """Provide workspace module info to all templates."""
    path = request.path
    is_ws = is_workspace_path(path)

    # User profile pages (/<username>/...) should also show workspace chrome
    if not is_ws and request.user.is_authenticated:
        is_ws = _is_user_profile_path(path)

    active_name = extract_module_from_path(path) if is_ws else None
    # Pages with a real module match get workspace sidebars (AI, worktree, viewer).
    # Extra workspace paths (e.g. /accounts/) get the tab bar but no sidebars.
    has_panes = is_ws and active_name is not None
    # Non-module workspace pages (accounts, profile) belong under Hub
    if is_ws and active_name is None:
        active_name = "hub"

    all_modules = get_all_modules()
    modules = _filter_modules_for_user(request, all_modules)

    for mod in modules:
        mod.is_active = mod.name == active_name

    active_mod = None
    if active_name:
        active_mod = next((m for m in modules if m.name == active_name), None)

    # Capitalized display name for the module header (e.g. "Hub", "Writer")
    active_label = (
        active_mod.label if active_mod and hasattr(active_mod, "label") else None
    )
    if not active_label and active_name:
        active_label = active_name.capitalize()

    return {
        "is_workspace_page": is_ws,
        "workspace_has_panes": has_panes,
        "workspace_modules": modules,
        "workspace_module_names_csv": ",".join(m.name for m in modules),
        "active_module_name": active_name,
        "active_module": active_mod,
        "active_module_label": active_label,
    }


def _is_user_profile_path(path: str) -> bool:
    """Check if path is a user profile page (/<username>/...)."""
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return False
    first = parts[0]
    # Skip registered module names
    from .registry import _registry_by_name

    if first in _registry_by_name:
        return False
    # Skip known non-user URL prefixes
    _NON_USER_PREFIXES = {
        "admin",
        "api",
        "static",
        "media",
        "auth",
        "healthz",
        "new",
        "files",
        "accounts",
        "public",
        "invite",
        "dev",
        "docs",
        "server-status",
        "__reload__",
    }
    return first not in _NON_USER_PREFIXES


def _filter_modules_for_user(request, modules):
    """Filter and reorder modules based on user's apps installations."""
    if not request.user.is_authenticated:
        return modules

    try:
        from apps.apps_app.models import AppsModule, ModuleInstallation

        installations = {
            inst.module.module_name: inst
            for inst in ModuleInstallation.objects.filter(
                user=request.user
            ).select_related("module")
        }

        # Populate apps status from AppsModule directly
        mp_statuses = dict(
            AppsModule.objects.filter(
                module_name__in=[m.name for m in modules]
            ).values_list("module_name", "status")
        )
        for mod in modules:
            db_status = mp_statuses.get(mod.name)
            if db_status:
                mod.status = db_status
    except Exception:
        # apps_app not migrated yet or other DB issue
        return modules

    if not installations:
        # No installations = first-time user, show default-enabled modules
        return [m for m in modules if m.default_enabled]

    # Show modules unless explicitly disabled via installation record
    visible = []
    for idx, mod in enumerate(modules):
        inst = installations.get(mod.name)
        if inst is None:
            # No record = default visible, keep registry order
            mod.order = (idx + 1) * 10
            visible.append(mod)
        elif inst.is_enabled:
            mod.order = inst.tab_order
            visible.append(mod)

    visible.sort(key=lambda m: m.order)
    return visible


# EOF
