#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workspace home launcher — app-grid home page (approved design 2026-07-07).

Serves the iPhone-style app grid at the workspace root ("/") and /apps/: a
responsive tile grid IS the home. Pin-to-sidebar state lives in
launcher_pins.py (re-exported below).

Django stays thin here: this module only assembles registry data
(workspace module registry + published store apps) for the template.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import get_language

from apps.infra.workspace_app.registry import get_all_modules

from ..models import AppsModule, ModuleInstallation, PlannedAppInterest
from ..planned_apps import visible_planned_apps
from ..services.first_run import checklist_context, should_show_checklist
from ..services.launcher_display import get_display_overrides, get_favorites
from ..services.launcher_dock import get_dock_apps
from ..services.launcher_links import get_launcher_links, get_link_tile_orders
from ..services.manifest_display import prettify_module_name
from .helpers import (
    can_view_internal_app,
    ensure_builtin_modules,
)
from .launcher_order import (
    DEFAULT_LAUNCHER_ORDER,  # noqa: F401  (re-export)
    LAUNCHER_GROUPS,
    TRAILING_APPS,
    group_cells,
    group_of,
    group_rank,
)
from .launcher_order import default_order_value as _default_order_value

# Sidebar pin state lives in launcher_pins.py; re-exported so existing imports
# (views/__init__.py, the workspace context processor, tests) keep working.
from .launcher_pins import (  # noqa: F401  (re-export)
    _MI_DEFAULT_TAB_ORDER,
    MAX_PINNED_MODULES,
    api_pin,
    default_pinned_module_names,
    get_pinned_module_names,
    seed_default_pins,
)

logger = logging.getLogger(__name__)

# Store apps published within this window get a NEW badge.
NEW_BADGE_DAYS = 14

# Model default for DevInstallation.tab_order (see launcher_pins for the
# ModuleInstallation one): a row still holding it was never explicitly reordered.
_DEV_DEFAULT_TAB_ORDER = 95

# Tombstones for retired/renamed built-ins. Existing database rows can remain
# until the deployment migration runs; they must never reappear as community
# apps in step 2 below.
_RETIRED_MODULE_IDS = frozenset({"home", "discovery", "slides"})

# Rendered as an empty "+" slot, not an app (operator, 2026-09-14): always the
# last cell of Work, never reorderable, never dockable.
APP_CREATOR_SLOT = "create-app"


def _is_dev_only(visibility: str, row) -> bool:
    """Whether a tile is still a work in progress, from EXISTING metadata only.

    Two fields already say that, and nothing new is invented here:
      * ``visibility == "internal"``: the registry's own definition is "staff /
        operators only (WIP apps before dogfood is stable)" (registry.py). Who
        may SEE such a tile is unchanged (the release-channel gate in
        _build_tiles still hides it from anyone not entitled); an entitled
        viewer now also sees that it is unfinished.
      * ``AppsModule.status == "wip"``: the catalogue's "Work in Progress".
    """
    return visibility == "internal" or getattr(row, "status", "") == "wip"


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



def _planned_tiles(user, real_app_names: set[str]) -> list[dict]:
    """Coming-soon tiles for planned apps no real app has replaced."""
    language = get_language() or "en"
    interests: set[tuple[str, str]] = set()
    if user.is_authenticated:
        interests = set(
            PlannedAppInterest.objects.filter(user=user).values_list("app_id", "kind")
        )
    return [
        {
            "name": app.id,
            "label": app.name(language),
            "icon_fa": app.icon,
            "category": app.category,
            "description": app.description(language),
            "is_planned": True,
            "icon_badge": "",
            "is_dev_only": False,
            "launch_url": "",
            "detail_url": "",
            "version": "",
            "version_label": "",
            "is_pinned": False,
            "is_new": False,
            "availability": "coming_soon",
            "is_launchable": False,
            "is_installed": False,
            "notified": (app.id, "notify") in interests,
            "building": (app.id, "build") in interests,
            # brief = the planned id; description = the brief text to prefill
            # until #859's create view reads the brief itself.
            "create_url": "/apps/create/?"
            + urlencode(
                {"name": app.name_en, "brief": app.id, "description": app.brief}
            ),
        }
        for app in visible_planned_apps(real_app_names)
    ]


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
    display_overrides = get_display_overrides(request.user)
    favorite_names = set(get_favorites(request.user))
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
    seen: set[str] = set(_RETIRED_MODULE_IDS)

    # 1. Workspace module registry — same source that builds the sidebar.
    # "internal" visibility is a RELEASE-CHANNEL gate, not an admin-role gate
    # (card hub-cards-internal-entitlement-20260913): on a development
    # deployment every authenticated team member sees internal apps (the
    # channel flag), anonymous users never do; staff see them everywhere.
    can_internal = can_view_internal_app(request.user)
    for mod in get_all_modules():
        # Release-channel gate: internal/WIP apps are hidden when the user is
        # not entitled (compass §8 L281-292, §21 L642-643).
        if not can_internal and mod.visibility == "internal":
            seen.add(mod.name)
            continue
        # NO mount gate here. Operator ruling 2026-09-14 15:48Z: Cards and
        # Agents are PRE-INSTALLED apps shown to everyone; only their CONTENT
        # depends on the user ("removing the whole app is wrong"). An earlier
        # version hid their tiles with can_open_mounted_app(); the mounts keep
        # their own per-user handling, the grid does not second-guess them.
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
        availability = mod.availability or (row.availability if row else "available")
        tiles.append(
            {
                "name": mod.name,
                "label": mod.label,
                "icon_fa": mod.icon_fa or "fas fa-puzzle-piece",
                "icon_badge": mod.icon_badge,
                "is_dev_only": _is_dev_only(mod.visibility, row),
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
                "description": mod.ai_hint or (row.short_description if row else ""),
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
                "icon_badge": "",
                "is_dev_only": _is_dev_only(row.visibility, row),
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
                    "icon_badge": "",
                    # A dev install is the developer's own unpublished work:
                    # nobody else can see it, which is what "dev-only" means.
                    "is_dev_only": True,
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

    # 4. Built-in link tiles (Chat, Settings): an existing hub page, not an app.
    # See services/launcher_links.py for why they stay out of the registry.
    # They have no AppsModule row, so a user's drag position for them is kept
    # on the launcher's own (App Store) installation row instead.
    if request.user.is_authenticated:
        user_orders.update(get_link_tile_orders(request.user))
    for link in get_launcher_links():
        if link.name in seen:
            continue
        tiles.append(
            {
                "name": link.name,
                "label": link.label,
                "icon_fa": link.icon,
                "icon_badge": "",
                "is_dev_only": False,
                "is_link": True,
                "launch_url": link.url,
                "category": link.category,
                "availability": "available",
                "is_launchable": True,
                "description": link.description,
                "version": "",
                "version_label": "",
                "is_installed": True,
                "is_pinned": False,
                "is_new": False,
                "detail_url": "",
            }
        )
        seen.add(link.name)

    # 5. Planned apps: a Coming-soon tile until a real app takes the id.
    tiles.extend(
        _planned_tiles(request.user, seen | installed_names | {t["name"] for t in tiles})
    )

    # Display overrides affect only presentation. Canonical ids, URLs, and
    # manifest/catalog metadata remain untouched.
    for tile in tiles:
        tile["manifest_label"] = tile["label"]
        tile["manifest_icon_fa"] = tile["icon_fa"]
        tile["icon_color"] = ""
        override = display_overrides.get(tile["name"], {})
        tile["label"] = override.get("display_name") or tile["label"]
        tile["icon_fa"] = override.get("icon") or tile["icon_fa"]
        tile["icon_color"] = override.get("icon_color") or ""
        row = catalog.get(tile["name"])
        tile["can_uninstall"] = bool(
            row and not row.is_builtin and tile["name"] in installed_names
        )
        tile["can_edit_display"] = bool(row)
        tile["is_favorite"] = tile["name"] in favorite_names

    # Apply order: the GROUP first (groups never interleave, operator
    # 2026-09-14), then explicit per-user positions, then the curated default.
    # Ties break by label so the grid render is deterministic.
    # Once the user has reordered, planned tiles (never saved) go last in
    # their group; the App Creator slot (TRAILING_APPS) is always after them.
    def _position(tile: dict) -> int:
        if tile["name"] in TRAILING_APPS:
            return 2_000_000
        if tile["name"] in user_orders:
            return user_orders[tile["name"]]
        if tile.get("is_planned") and user_orders:
            return 1_000_000
        return _default_order_value(tile["name"])

    tiles.sort(key=lambda t: (group_rank(t["name"]), _position(t), t["label"].lower()))
    for tile in tiles:
        tile["user_ordered"] = tile["name"] in user_orders
        tile["group"] = group_of(tile["name"])
        tile["is_add_slot"] = tile["name"] == APP_CREATOR_SLOT
    return tiles


def launcher_context(request) -> dict:
    """Template context for the launcher home page."""
    ensure_builtin_modules()
    tiles = _build_tiles(request)
    dock_apps = set(get_dock_apps(request.user)) - {APP_CREATOR_SLOT}
    grid_tiles = [tile for tile in tiles if tile["name"] not in dock_apps]
    favorite_order = get_favorites(request.user)
    by_name = {tile["name"]: tile for tile in tiles}
    favorite_tiles = []
    for name in favorite_order:
        if name in by_name:
            alias = dict(by_name[name])
            alias["is_favorite_alias"] = True
            alias["can_uninstall"] = False
            favorite_tiles.append(alias)
    return {
        "first_run": (
            checklist_context(request.user)
            if request.user.is_authenticated
            and should_show_checklist(request.user)
            else None
        ),
        # Every app the user can open, wherever it sits (grid or dock).
        "tiles": tiles,
        # The grid: 4-column group bands holding only the apps NOT in the dock.
        "groups": group_cells(grid_tiles),
        "favorite_tiles": favorite_tiles,
        # Kept in a <template> so dragging an app out of the dock can restore its tile.
        "dock_tiles": [tile for tile in tiles if tile["name"] in dock_apps],
        "launcher_groups": LAUNCHER_GROUPS,
        "installed_count": sum(1 for t in tiles if t["is_installed"]),
        "max_pins": MAX_PINNED_MODULES,
        "is_guest_launcher": False,
        "guest_role": "",
    }


@login_required
def launcher(request):
    """Workspace home — the app-launcher grid (served at the root URL)."""
    return render(request, "apps_app/launcher.html", launcher_context(request))


# EOF
