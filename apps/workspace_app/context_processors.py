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
    active_name = extract_module_from_path(path) if is_ws else None

    all_modules = get_all_modules()
    modules = _filter_modules_for_user(request, all_modules)

    for mod in modules:
        mod.is_active = mod.name == active_name

    active_mod = None
    if active_name:
        active_mod = next((m for m in modules if m.name == active_name), None)

    return {
        "is_workspace_page": is_ws,
        "workspace_modules": modules,
        "workspace_module_names_csv": ",".join(m.name for m in modules),
        "active_module_name": active_name,
        "active_module": active_mod,
    }


def _filter_modules_for_user(request, modules):
    """Filter and reorder modules based on user's marketplace installations."""
    if not request.user.is_authenticated:
        return modules

    try:
        from apps.marketplace_app.models import MarketplaceModule, ModuleInstallation

        installations = {
            inst.module.module_name: inst
            for inst in ModuleInstallation.objects.filter(
                user=request.user
            ).select_related("module")
        }

        # Populate marketplace status from MarketplaceModule directly
        mp_statuses = dict(
            MarketplaceModule.objects.filter(
                module_name__in=[m.name for m in modules]
            ).values_list("module_name", "status")
        )
        for mod in modules:
            mod.status = mp_statuses.get(mod.name, "")
    except Exception:
        # marketplace_app not migrated yet or other DB issue
        return modules

    if not installations:
        # No installations = first-time user, show all modules
        return modules

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
