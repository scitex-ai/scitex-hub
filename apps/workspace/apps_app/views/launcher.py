#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workspace home launcher — app-grid home page (approved design 2026-07-07).

Serves the iPhone-style app grid at the workspace root ("/"): a
responsive tile grid IS the home, with per-user pin-to-sidebar
persistence (capped at MAX_PINNED_MODULES).

Django stays thin here: this module only assembles registry data
(workspace module registry + published store apps) for the template.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.infra.workspace_app.registry import get_all_modules

from ..models import AppsModule, ModuleInstallation
from ..services.manifest_display import prettify_module_name
from .helpers import ensure_builtin_modules

logger = logging.getLogger(__name__)

# Sidebar pin cap — keeps the reduced sidebar scannable.
MAX_PINNED_MODULES = 5

# Store apps published within this window get a NEW badge.
NEW_BADGE_DAYS = 14

# Curated default tile order. The raw registry order read "weird" to the
# operator (Telegram 992/997, 2026-07-12); this gives the research apps a
# natural first-screen order. Modules not listed sort after these by label.
# A per-user drag-reorder (api_reorder) overrides this entirely.
DEFAULT_LAUNCHER_ORDER = [
    "home",
    "writer",
    "scholar",
    "figrecipe",
    "console",
    "discovery",
    "clew",
    "tools",
    "docs",
    "todo",
    "store",
]
_DEFAULT_ORDER_INDEX = {name: i for i, name in enumerate(DEFAULT_LAUNCHER_ORDER)}

# Model defaults for the tab_order columns. A row still holding the default
# was created incidentally (e.g. by pinning), not by an explicit launcher
# reorder — so it keeps the curated position rather than jumping the tile.
_MI_DEFAULT_TAB_ORDER = 50
_DEV_DEFAULT_TAB_ORDER = 95

# The sidebar renders its own Home entry, so pinning "home" would double it.
_SIDEBAR_HOME_MODULE = "home"


def _default_order_value(name: str) -> int:
    """Curated launcher position (lower sorts earlier).

    Curated apps occupy 10..110; anything uncurated sorts after them (by
    label). Reorder positions written by api_reorder live at 1000+, well
    clear of both, so an explicit user choice always wins.
    """
    idx = _DEFAULT_ORDER_INDEX.get(name)
    if idx is not None:
        return (idx + 1) * 10
    return 500_000


def _version_label(version: str) -> str:
    """Format a manifest version for tile display.

    "0.14.0" -> "v0.14.0"; "dev" -> "dev" (dev-installed apps carry no
    manifest version); "" -> "" (degrade gracefully — the tile hides the
    label rather than showing a fake version). Never raises.
    """
    v = (version or "").strip()
    if not v:
        return ""
    if v == "dev":
        return "dev"
    return v if v.lower().startswith("v") else f"v{v}"


def is_guest_launcher_user(user) -> bool:
    """True for pool visitors (visitor-*) and the shared readonly-visitor.

    Guest-mode launcher (card hub-visitor-ux-allapps): visitors keep the
    app grid but get a prominent Sign in / Sign up call-to-action instead
    of a personalized greeting. Role mapping is delegated to the canonical
    session-role model (no scattered username checks).
    """
    from apps.infra.project_app.services.visitor_pool import (
        ROLE_READONLY_VISITOR,
        ROLE_VISITOR,
        get_user_role,
    )

    return get_user_role(user) in (ROLE_VISITOR, ROLE_READONLY_VISITOR)


def guest_role_for(user) -> str:
    """Which KIND of guest this is — the two are very different experiences.

    A pool ``visitor`` gets a real writable workspace for the session; the
    shared ``readonly-visitor`` fallback can only look. Telling both "sign in
    to unlock editing" misleads the visitor, who can already edit. Returns
    "visitor" | "readonly_visitor" | "" (not a guest).
    """
    from apps.infra.project_app.services.visitor_pool import (
        ROLE_READONLY_VISITOR,
        ROLE_VISITOR,
        get_user_role,
    )

    role = get_user_role(user)
    if role == ROLE_VISITOR:
        return "visitor"
    if role == ROLE_READONLY_VISITOR:
        return "readonly_visitor"
    return ""


def default_pinned_module_names() -> list[str]:
    """The pin set a user starts with, before they pin anything themselves.

    Reuses DEFAULT_LAUNCHER_ORDER so the sidebar and the launcher grid agree
    on which apps lead — no second curated list to drift. "home" is excluded
    because the sidebar renders its own Home entry above the pinned loop.
    """
    registered = {mod.name for mod in get_all_modules()}
    return [
        name
        for name in DEFAULT_LAUNCHER_ORDER
        if name != _SIDEBAR_HOME_MODULE and name in registered
    ][:MAX_PINNED_MODULES]


def _appsmodule_catalog(names: list[str]) -> dict[str, AppsModule]:
    """AppsModule rows for the given module names, keyed by name."""
    return {
        app.module_name: app
        for app in AppsModule.objects.filter(module_name__in=names)
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


def _build_tiles(request) -> list[dict]:
    """Assemble launcher tiles: registry modules + published store apps."""
    catalog = {m.module_name: m for m in AppsModule.objects.all()}

    installed_names: set[str] = set()
    if request.user.is_authenticated:
        installed_names = set(
            ModuleInstallation.objects.filter(user=request.user).values_list(
                "module__module_name", flat=True
            )
        )
    pinned_names = set(get_pinned_module_names(request.user))
    new_cutoff = timezone.now() - timedelta(days=NEW_BADGE_DAYS)

    # Per-user launcher order set by drag-reorder (api_reorder). Only rows
    # whose tab_order differs from the model default count as an explicit
    # user choice; default-valued rows are incidental (e.g. pins).
    user_orders: dict[str, int] = {}
    if request.user.is_authenticated:
        for _name, _order in ModuleInstallation.objects.filter(
            user=request.user
        ).values_list("module__module_name", "tab_order"):
            if _order != _MI_DEFAULT_TAB_ORDER:
                user_orders[_name] = _order

    tiles: list[dict] = []
    seen: set[str] = set()

    # 1. Workspace module registry — same source that builds the sidebar.
    for mod in get_all_modules():
        # Some registered modules are workspace panes / nav items, not
        # standalone launcher apps (Clew opens within a manuscript; comms
        # is reached from the workspace rather than the grid). They opt out
        # of the grid via the manifest `show_in_launcher` flag but stay in
        # the tab bar. NOTE the comms module is the real-time MESSAGING app
        # at /apps/comms/ — not the /chat/ LLM pane, which this comment used
        # to conflate it with and which has no registry entry at all.
        # Mark them seen BEFORE skipping: step 2 below re-adds any public
        # AppsModule row not in `seen`, which would put the tile straight
        # back on the grid.
        if not mod.show_in_launcher:
            seen.add(mod.name)
            continue
        row = catalog.get(mod.name)
        # Availability: manifest declaration wins (ships with the app);
        # the catalog row carries it for store-published registrations
        # (their manifest lives in another repo — migration 0017 seeds
        # the operator-named coming_soon rows). Same precedence rule as
        # category below.
        availability = mod.availability or (
            row.availability if row else "available"
        )
        tiles.append(
            {
                "name": mod.name,
                "label": mod.label,
                "icon_fa": mod.icon_fa or "fas fa-puzzle-piece",
                "launch_url": mod.get_url(),
                "availability": availability,
                # Coming-soon tiles must never navigate (operator: a tap
                # effect is fine, navigation is not). The template drops
                # the href from this single flag.
                "is_launchable": availability != "coming_soon",
                # The MANIFEST wins: an app declares what it is, and that
                # declaration ships with the app. The AppsModule row is a
                # per-deployment catalogue entry that a freshly-mounted plugin
                # simply does not have yet — reading it first is what made every
                # unseeded app fall through to "other" and render with the
                # generic yellow puzzle gradient.
                "category": mod.category or (row.category if row else "other"),
                "description": row.short_description if row else mod.ai_hint,
                # Deployed version from the app manifest (SSOT). Empty when the
                # manifest omits it — the tile hides the label, never breaks.
                "version": mod.version,
                "version_label": _version_label(mod.version),
                "is_installed": True,  # registry modules are built in
                "is_pinned": mod.name in pinned_names,
                "is_new": False,
                "detail_url": f"/apps/store/{mod.name}/",
            }
        )
        seen.add(mod.name)

    # 2. Published store apps not in the registry (community apps).
    # Apps in this branch were NOT loaded into the workspace registry
    # (load_approved_apps registers every public app with a project at
    # startup), so there is no route that can render them —
    # /apps/<module_name>/ is not mounted and 404'd for installed apps
    # (nav-404 batch #5). The store detail page is the only truthful
    # navigation target until the app is registered.
    published = AppsModule.objects.filter(visibility="public").exclude(
        module_name__in=seen
    )
    for row in published:
        installed = row.module_name in installed_names
        tiles.append(
            {
                "name": row.module_name,
                # The MANIFEST-fed columns win (populated at publish/seed
                # time — the manifest is the SSoT, mirroring the tile
                # category fix). A blank column means the manifest declared
                # nothing: fall back to a prettified slug / the generic
                # puzzle icon — visible and honest, never fabricated.
                "label": row.label or prettify_module_name(row.module_name),
                "icon_fa": row.icon or "fas fa-puzzle-piece",
                "launch_url": f"/apps/store/{row.module_name}/",
                "category": row.category,
                # No registry entry here, so the catalog row IS the SSoT.
                "availability": row.availability,
                "is_launchable": row.availability != "coming_soon",
                "description": row.short_description,
                # Community store apps are not in the registry (no manifest
                # here); omit the version rather than invent one.
                "version": "",
                "version_label": "",
                "is_installed": installed,
                "is_pinned": row.module_name in pinned_names,
                "is_new": row.created_at is not None and row.created_at >= new_cutoff,
                "detail_url": f"/apps/store/{row.module_name}/",
            }
        )

    # 3. Dev-installed apps (personal — previously reachable from the sidebar).
    if request.user.is_authenticated:
        from ..models import DevInstallation

        for dev in DevInstallation.objects.filter(user=request.user, is_enabled=True):
            if dev.tab_order != _DEV_DEFAULT_TAB_ORDER:
                user_orders[dev.module_name] = dev.tab_order
            tiles.append(
                {
                    "name": dev.module_name,
                    "label": dev.label or dev.source_repo,
                    "icon_fa": dev.icon or "fas fa-puzzle-piece",
                    "launch_url": f"/apps/{dev.module_name}/",
                    "category": "other",
                    # Dev installs are the developer's own work-in-progress;
                    # gating their launch would block the dev loop itself.
                    "availability": "available",
                    "is_launchable": True,
                    "description": dev.description,
                    # Dev-installed apps carry no manifest version — mark "dev".
                    "version": "dev",
                    "version_label": "dev",
                    "is_installed": True,
                    "is_pinned": False,
                    "is_new": False,
                    "detail_url": f"/apps/{dev.module_name}/",
                }
            )

    # Apply order: explicit per-user positions win; otherwise the curated
    # default. Ties break by label so the grid render is deterministic.
    tiles.sort(
        key=lambda t: (
            user_orders.get(t["name"], _default_order_value(t["name"])),
            t["label"].lower(),
        )
    )
    return tiles


def launcher_context(request) -> dict:
    """Template context for the launcher home page."""
    ensure_builtin_modules()
    tiles = _build_tiles(request)
    return {
        "tiles": tiles,
        "installed_count": sum(1 for t in tiles if t["is_installed"]),
        "max_pins": MAX_PINNED_MODULES,
        # Guest mode: visitors see tiles + a prominent Sign in / Sign up CTA.
        "is_guest_launcher": is_guest_launcher_user(request.user),
        # ...but a writable pool visitor and a read-only fallback are NOT the
        # same experience, so the copy must differ (operator, 2026-07-12).
        "guest_role": guest_role_for(request.user),
    }


@login_required
def launcher(request):
    """Workspace home — the app-launcher grid (served at the root URL)."""
    return render(request, "apps_app/launcher.html", launcher_context(request))


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
