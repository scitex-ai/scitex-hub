#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in LINK tiles: launcher tiles that open an existing hub page.

Operator, 2026-09-14: the Home grid gains a Settings tile (the same account
Settings page the hamburger menu opens) and a Chat tile (the same /chat/ route
the dock opens). Neither is an app. Settings is part of accounts_app and Chat is
a root-mounted workspace pane (core_panes.py), so each already has its own
route, view and nav entry.

WHY THESE ARE NOT WORKSPACE-REGISTRY MODULES. A registry module is more than a
tile. The same list feeds the module tab bar, the sidebar, the App Store
catalogue (seed_apps creates an AppsModule row for each one), the docs index and
``extract_module_from_path``. That last one decides which module is ACTIVE for
a URL, so registering "settings" at /accounts/settings/ would change which
sidebar context every account page renders in. A link tile needs none of that.
It gets a small manifest of its own (label, icon, category, url) under
``apps_app/launcher_links/``, and ``launcher._build_tiles`` appends it to the
grid. Nothing else reads it.

A link tile has no AppsModule row, so it cannot be pinned to the sidebar (the
pin API is keyed on that row) and has no store detail page. The template marks
it ``data-link-only="1"`` and the context popover drops those two actions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_LINKS_DIR = Path(__file__).resolve().parent.parent / "launcher_links"

#: Every key a link manifest must carry, non-empty.
_REQUIRED = ("name", "label", "icon", "category", "url")


@dataclass(frozen=True)
class LauncherLink:
    """One built-in link tile, read from ``launcher_links/<name>.json``."""

    name: str
    label: str
    icon: str
    category: str
    url: str
    description: str = ""


def _load(path: Path) -> LauncherLink:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in _REQUIRED if not data.get(key)]
    if missing:
        raise ValueError(f"launcher link {path.name} is missing {missing}")
    return LauncherLink(
        name=data["name"],
        label=data["label"],
        icon=data["icon"],
        category=data["category"],
        url=data["url"],
        description=data.get("description", ""),
    )


@lru_cache(maxsize=1)
def get_launcher_links() -> tuple[LauncherLink, ...]:
    """All built-in link tiles, in file-name order (the grid re-sorts them).

    A malformed file is logged and skipped rather than 500'ing the launcher, which
    is the same stance the workspace registry takes on a bad manifest.
    """
    links = []
    for path in sorted(_LINKS_DIR.glob("*.json")):
        try:
            links.append(_load(path))
        except Exception:
            logger.exception("[launcher] could not load link tile %s", path)
    return tuple(links)


def get_launcher_link(name: str) -> LauncherLink | None:
    """The link tile called ``name``, or None."""
    return next((link for link in get_launcher_links() if link.name == name), None)


# ---------------------------------------------------------------------------
# Drag-reorder persistence for link tiles
# ---------------------------------------------------------------------------
# A user's launcher order is stored per tile as ModuleInstallation.tab_order,
# and a link tile has no AppsModule row to hang that on. Without somewhere to
# keep it, the first drag would push every OTHER tile to 1000+ while Chat and
# Settings stayed at their curated 10..170, jumping them to the front. The App
# Store module IS apps_app, the app that owns the launcher, so its installation
# row carries the link positions in ``config[LINK_ORDER_KEY]``.
LINK_ORDER_KEY = "launcher_link_order"
_LAUNCHER_OWNER_MODULE = "store"


def _owner_installation(user, create: bool):
    from ..models import AppsModule, ModuleInstallation

    module = AppsModule.objects.filter(module_name=_LAUNCHER_OWNER_MODULE).first()
    if module is None:
        return None
    if not create:
        return ModuleInstallation.objects.filter(user=user, module=module).first()
    inst, _ = ModuleInstallation.objects.get_or_create(
        user=user,
        module=module,
        # The model-default tab_order marks the row incidental, so creating it
        # here never reads as an explicit reorder of the App Store tile itself.
        defaults={"is_enabled": True, "tab_order": 50},
    )
    return inst


def get_link_tile_orders(user) -> dict[str, int]:
    """The user's saved launcher positions for link tiles (``{}`` if none)."""
    inst = _owner_installation(user, create=False)
    saved = (inst.config or {}).get(LINK_ORDER_KEY, {}) if inst else {}
    names = {link.name for link in get_launcher_links()}
    return {
        name: int(pos)
        for name, pos in saved.items()
        if name in names and isinstance(pos, int)
    }


def save_link_tile_orders(user, order: list[str]) -> None:
    """Persist link-tile positions from a posted launcher order.

    Uses the same ``1000 + index`` scale api_reorder writes for real modules, so
    the two interleave exactly as the user dropped them.
    """
    names = {link.name for link in get_launcher_links()}
    positions = {name: 1000 + idx for idx, name in enumerate(order) if name in names}
    if not positions:
        return
    inst = _owner_installation(user, create=True)
    if inst is None:
        return
    config = inst.config or {}
    config[LINK_ORDER_KEY] = positions
    inst.config = config
    inst.save(update_fields=["config"])


# EOF
