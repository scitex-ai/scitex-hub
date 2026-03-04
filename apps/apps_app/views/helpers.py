#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps view helpers — shared utilities for pages and API."""

from __future__ import annotations

import logging

from apps.workspace_app.registry import get_module

from ..models import (
    AppsModule,
    ModuleInstallation,
    ModuleStar,
)

logger = logging.getLogger(__name__)

# Module-level flag — ensures built-in modules exist on first apps visit
_builtins_ensured = False


def ensure_builtin_modules():
    """Ensure all built-in modules exist in DB. Runs once per process."""
    global _builtins_ensured
    if _builtins_ensured:
        return

    from apps.workspace_app.registry import get_all_modules

    registered_names = {m.name for m in get_all_modules()}
    existing_names = set(
        AppsModule.objects.filter(is_builtin=True).values_list("module_name", flat=True)
    )

    if registered_names <= existing_names:
        _builtins_ensured = True
        return

    try:
        from django.db import transaction

        from ..management.commands.seed_apps import (
            ensure_builtin_modules as seed_builtins,
        )

        with transaction.atomic():
            created, _ = seed_builtins()
        if created:
            logger.info("[apps] Auto-seeded %d built-in modules", created)
    except Exception:
        logger.exception("[apps] Failed to auto-seed built-in modules")
    _builtins_ensured = True


def can_view_module(user, app_module):
    """Check if user can view this module based on visibility."""
    if app_module.visibility == "public" or app_module.is_builtin:
        return True
    if user.is_authenticated and app_module.author == user:
        return True
    if user.is_authenticated and user.is_staff:
        return True
    return False


def browse_context(request, current_project=None):
    """Build browse page context — all modules returned, filtering is client-side."""
    ensure_builtin_modules()

    modules = AppsModule.objects.filter(visibility="public").order_by(
        "-star_count", "-install_count"
    )

    # Modules disabled by default (installed but hidden from tab bar)
    DEFAULT_DISABLED = {"example", "modulemaker"}

    # Annotate with user-specific state
    install_map = {}  # module_name -> {is_enabled, tab_order}
    starred_names = set()
    if request.user.is_authenticated:
        for row in ModuleInstallation.objects.filter(user=request.user).values_list(
            "module__module_name", "is_enabled", "tab_order"
        ):
            install_map[row[0]] = {"is_enabled": row[1], "tab_order": row[2]}
        starred_names = set(
            ModuleStar.objects.filter(user=request.user).values_list(
                "module__module_name", flat=True
            )
        )

    module_list = []
    for mp in modules:
        reg = get_module(mp.module_name)
        installed = mp.is_builtin or mp.module_name in install_map
        info = install_map.get(mp.module_name)
        if info:
            enabled = info["is_enabled"]
            tab_order = info["tab_order"]
        else:
            # Builtin without explicit installation record
            enabled = mp.module_name not in DEFAULT_DISABLED
            tab_order = reg.order if reg else 50
        module_list.append(
            {
                "app": mp,
                "reg": reg,
                "is_installed": installed,
                "is_enabled": enabled,
                "tab_order": tab_order,
                "is_starred": mp.module_name in starred_names,
            }
        )

    from ..models import CATEGORY_CHOICES, DevInstallation

    # Dev installations for the "My Dev Apps" section
    dev_apps = []
    if request.user.is_authenticated:
        dev_apps = list(DevInstallation.objects.filter(user=request.user))

    return {
        "current_project": current_project,
        "modules": module_list,
        "categories": CATEGORY_CHOICES,
        "dev_apps": dev_apps,
    }


# EOF
