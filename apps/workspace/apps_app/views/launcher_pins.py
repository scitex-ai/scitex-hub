#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sidebar pins for the launcher: default pin set, seeding, reading and toggling.

Extracted from ``launcher.py`` (which re-exports everything here, so existing
imports keep working) when the Home + dock redesign pushed that module past the
line budget. Tile assembly stayed in ``launcher.py``; the per-user pin state it
reads lives here.
"""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.infra.workspace_app.registry import get_all_modules

from ..models import AppsModule, ModuleInstallation
from .helpers import ensure_builtin_modules
from .launcher_order import DEFAULT_LAUNCHER_ORDER

logger = logging.getLogger(__name__)

# Sidebar pin cap — keeps the reduced sidebar scannable.
MAX_PINNED_MODULES = 5

# Model defaults for the tab_order columns. A row still holding the default
# was created incidentally (e.g. by pinning), not by an explicit launcher
# reorder — so it keeps the curated position rather than jumping the tile.
_MI_DEFAULT_TAB_ORDER = 50

# The sidebar renders its own Home entry, so pinning "home" would double it.
_SIDEBAR_HOME_MODULE = "home"


def default_pinned_module_names() -> list[str]:
    """The pin set a user starts with, before they pin anything themselves.

    Reuses DEFAULT_LAUNCHER_ORDER so the sidebar and the launcher grid agree
    on which apps lead — no second curated list to drift. "home" is excluded
    because the sidebar renders its own Home entry above the pinned loop.

    An app that opted OUT of the grid (manifest ``show_in_launcher: false``)
    is excluded too. Leading the sidebar with an app that has no tile is the
    drift this function's own docstring exists to prevent, and it is what made
    "hide Console" nearly a half-measure: MAX_PINNED_MODULES is 5, Console sat
    fifth in the curated list, so dropping only its tile would have left it
    pinned in the sidebar — still there, for a user told it was gone. Clew and
    Comms already declared the same flag and are excluded for the same reason;
    both are reached from where they belong (a manuscript, the workspace)
    rather than from a pin.

    Link tiles (Chat, Settings) and the reserved "stats" slot are not
    registered modules, so the ``registered`` filter drops them as well.
    """
    hidden = {mod.name for mod in get_all_modules() if not mod.show_in_launcher}
    registered = {mod.name for mod in get_all_modules()}
    return [
        name
        for name in DEFAULT_LAUNCHER_ORDER
        if name != _SIDEBAR_HOME_MODULE and name in registered and name not in hidden
    ][:MAX_PINNED_MODULES]


def _appsmodule_catalog(names: list[str]) -> dict[str, AppsModule]:
    """AppsModule rows for the given module names, keyed by name."""
    return {
        app.module_name: app for app in AppsModule.objects.filter(module_name__in=names)
    }


def _is_pool_account(user) -> bool:
    """Visitor-pool accounts: the rotating visitor-NNN slots + the shared
    read-only fallback. These are shared, recycled identities — seeding pins
    for them populates the sidebar for EVERY future visitor of that slot
    (operator report 2026-07-17: "the sidebar came back"), and their pin
    state is meaningless across the slot wipe anyway."""
    from apps.infra.project_app.services.visitor_pool import VisitorPool

    return user.username.startswith(VisitorPool.VISITOR_USER_PREFIX) or (
        user.username == VisitorPool.READONLY_VISITOR_USERNAME
    )


def seed_default_pins(user) -> bool:
    """Give a user their starting pins. Idempotent; True if it created any row.

    Pins only ever on row CREATION, so a module the user deliberately unpinned
    keeps its row (without the "pinned" key) and is never resurrected. Rows are
    real (not virtual) because api_pin reads the flag straight off the row — a
    virtual default would make the first unpin click *pin* instead.

    Seeded rows keep the model-default tab_order, which marks them incidental,
    so they never masquerade as an explicit drag-reorder.

    Pool accounts (visitor-NNN, readonly-visitor) are never seeded: visitors
    get the minimal sidebar and discover apps through the launcher grid.
    """
    if _is_pool_account(user):
        return False
    ensure_builtin_modules()
    names = default_pinned_module_names()
    catalog = _appsmodule_catalog(names)

    if len(catalog) < len(names):
        # ensure_builtin_modules() memoises on a PROCESS-GLOBAL flag and returns
        # before it ever looks at the DB, so it can report "already seeded" while
        # the rows are in fact gone (a test-transaction rollback, or a DB reset
        # against a warm process). Pinning nothing here would silently reinstate
        # the empty sidebar this function exists to prevent — so seed for real.
        from ..management.commands.seed_apps import (
            ensure_builtin_modules as seed_builtins,
        )

        with transaction.atomic():
            seed_builtins()
        catalog = _appsmodule_catalog(names)
        missing = [name for name in names if name not in catalog]
        if missing:
            logger.warning(
                "[launcher] No AppsModule row for default pins %s even after "
                "seeding — those apps will be absent from the sidebar.",
                missing,
            )

    created_any = False
    # Created in curated order, so ascending ids give the sidebar that order.
    for name in names:
        app_module = catalog.get(name)
        if app_module is None:
            continue
        _, created = ModuleInstallation.objects.get_or_create(
            user=user,
            module=app_module,
            defaults={
                "is_enabled": True,
                "tab_order": _MI_DEFAULT_TAB_ORDER,
                "config": {"pinned": True},
            },
        )
        created_any = created_any or created
    return created_any


def get_pinned_module_names(user) -> list[str]:
    """Names of modules the user pinned to the sidebar (stable order).

    No pins at all means the user has either never been seeded or unpinned
    everything. Seeding is idempotent, so the second case stays empty — an
    empty sidebar the user chose is respected.
    """
    if not user.is_authenticated:
        return []

    def _query() -> list[str]:
        return list(
            ModuleInstallation.objects.filter(user=user, config__pinned=True)
            .order_by("tab_order", "id")
            .values_list("module__module_name", flat=True)[:MAX_PINNED_MODULES]
        )

    names = _query()
    if not names and seed_default_pins(user):
        names = _query()
    return names


@login_required
@require_http_methods(["POST"])
def api_pin(request, module_name):
    """Toggle a module's pinned-to-sidebar flag (per-user, capped)."""
    ensure_builtin_modules()
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    inst = ModuleInstallation.objects.filter(
        user=request.user, module=app_module
    ).first()
    currently_pinned = bool(inst and (inst.config or {}).get("pinned"))

    if not currently_pinned:
        pinned_count = ModuleInstallation.objects.filter(
            user=request.user, config__pinned=True
        ).count()
        if pinned_count >= MAX_PINNED_MODULES:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        f"Pin limit reached ({MAX_PINNED_MODULES}). "
                        "Unpin another app first."
                    ),
                },
                status=400,
            )

    if inst is None:
        # Pinning implies the module is part of the user's workspace.
        inst = ModuleInstallation.objects.create(
            user=request.user, module=app_module, is_enabled=True, tab_order=50
        )

    config = inst.config or {}
    if currently_pinned:
        config.pop("pinned", None)
    else:
        config["pinned"] = True
    inst.config = config
    inst.save(update_fields=["config"])

    return JsonResponse(
        {
            "success": True,
            "pinned": not currently_pinned,
            "pinned_modules": get_pinned_module_names(request.user),
        }
    )


# EOF
