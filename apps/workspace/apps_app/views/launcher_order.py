#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Curated default launcher order — the one list every launcher surface sorts by.

Extracted from ``launcher.py`` so the workspace grid and the sidebar default
pins can share it without importing the whole launcher view module. (The
global-header "Apps" dropdown that also read it was removed on 2026-09-14: the
logo and the dock's Home button are the way back to the grid.)
"""

from __future__ import annotations

# Curated default tile order. The raw registry order read "weird" to the
# operator (Telegram 992/997, 2026-07-12); this gives the apps a natural
# first-screen order. Modules not listed sort after these by label.
# A per-user drag-reorder (api_reorder) overrides this entirely.
#
# THIS LIST — not the manifests — is what a user sees. _build_tiles enumerates
# get_all_modules() (manifest `order`) but then re-sorts every tile through
# default_order_value(), so editing a manifest's `order` moves nothing on the
# grid. Both are kept in step anyway: leaving them to disagree is what made
# that easy to get wrong. Operator, Telegram 4794, 2026-09-05:
# 「順番はスカラフィグレシピライター」 — Scholar, FigRecipe, Writer.
#
# GROUPS (operator, 2026-09-14 16:3xZ). The Home grid is 4 columns at every
# width so an app sits at the same position on every device. Apps are grouped,
# each group starts a new row and gets a soft colour band, and a group's last
# row keeps its empty cells rather than pulling the next group's app up:
#   FOUNDATION (基盤): My Projects, Agents, Cards, Storage, Files
#   WORK (作業):       Scholar, FigRecipe, (Stats), Writer, Chat, Tools
#   PUBLISH (発信):    Slides, Public Projects — showing work outside
#                      (proposed 2026-09-14, Telegram 6040; pending operator)
#   SYSTEM (システム): Settings, Docs, App Store
# Within a group the order is the operator's earlier order (infrastructure,
# then Scholar-FigRecipe-Stats-Writer, then Chat/Settings/Tools, then
# Docs/App Store/Storage). Each group carries role="group" and a translated
# aria-label, which launcher/grid.css also shows as the band's visible label.
#
# "stats" keeps its position although no Stats app exists yet: until it lands
# it is a visible Coming-soon tile (planned_apps.py), never an empty cell — an
# unexplained gap read as a broken grid in the 2026-09-14 walkthrough. The day
# the module lands it takes that position without touching this list. Give its manifest "order": 27
# (figrecipe is 25, writer 30). Chat and Settings are link tiles
# (services/launcher_links.py). Console and Clew opt out of the grid via
# show_in_launcher=false.
from dataclasses import dataclass

LAUNCHER_COLUMNS = 4


@dataclass(frozen=True)
class LauncherGroup:
    key: str
    label: str  # translated at render time ({% trans %})
    members: tuple[str, ...]


LAUNCHER_GROUPS: tuple[LauncherGroup, ...] = (
    LauncherGroup(
        "foundation",
        "Foundation",
        ("home", "agents", "todo", "storage", "files"),
    ),
    LauncherGroup(
        "work",
        "Work",
        (
            "scholar",
            "stats",  # a Coming-soon tile until the app ships (planned_apps.py)
            "figrecipe",
            "writer",
            "chat",  # link tile -> /chat/
            "clew",
            "create-app",  # App Creator: the empty "+" slot, always last in Work
        ),
    ),
    LauncherGroup(
        "publication",
        "Publication",
        ("slides", "discovery"),
    ),
    LauncherGroup(
        "system",
        "System",
        ("settings", "docs", "store"),  # settings = link tile; store = App Store
    ),
    LauncherGroup(
        "tools",
        "Tools",
        (
            "tools-image",
            "tools-pdf",
            "tools-text",
            "tools-developer",
            "tools-media",
            "console",
            # The aggregate route stays registered but hidden from the grid.
            "tools",
        ),
    ),
)

#: Uncurated apps (community store apps, dev installs) are applications.
DEFAULT_GROUP = "work"

#: Always the last tile of its group, whatever the user or a planned app does
#: (operator, 2026-09-14).
TRAILING_APPS = ("create-app",)

DEFAULT_LAUNCHER_ORDER = [name for group in LAUNCHER_GROUPS for name in group.members]
_GROUP_OF = {name: group.key for group in LAUNCHER_GROUPS for name in group.members}
_GROUP_RANK = {group.key: i for i, group in enumerate(LAUNCHER_GROUPS)}
_DEFAULT_ORDER_INDEX = {name: i for i, name in enumerate(DEFAULT_LAUNCHER_ORDER)}


def default_order_value(name: str) -> int:
    """Curated launcher position (lower sorts earlier).

    Curated apps occupy 10..170; anything uncurated sorts after them (by
    label). Reorder positions written by api_reorder live at 1000+, well
    clear of both, so an explicit user choice always wins WITHIN a group.
    """
    idx = _DEFAULT_ORDER_INDEX.get(name)
    if idx is not None:
        return (idx + 1) * 10
    planned = _planned_order_value(name)
    return planned if planned is not None else 500_000


def _planned_order_value(name: str) -> int | None:
    """A planned app sits right after its group's curated apps, in registry order."""
    from ..planned_apps import PLANNED_APPS

    ids = [app.id for app in PLANNED_APPS]
    if name not in ids:
        return None
    members = next(g.members for g in LAUNCHER_GROUPS if g.key == group_of(name))
    last = max(_DEFAULT_ORDER_INDEX[m] for m in members if m not in TRAILING_APPS)
    return (last + 1) * 10 + 1 + ids.index(name)


def group_of(name: str) -> str:
    """The group key an app belongs to."""
    from ..planned_apps import PLANNED_BY_ID

    if name in _GROUP_OF:
        return _GROUP_OF[name]
    planned = PLANNED_BY_ID.get(name)
    if planned and planned.group in _GROUP_RANK:
        return planned.group
    return DEFAULT_GROUP


def group_rank(name: str) -> int:
    """Sort rank of an app's group (groups never interleave)."""
    return _GROUP_RANK[group_of(name)]


def group_cells(tiles: list[dict]) -> list[dict]:
    """The tiles as groups of grid cells, in group order.

    ``tiles`` must already be sorted (group first, then position). Returns
    ``[{"key", "label", "cells"}]``. A group with no tiles is omitted.
    """
    groups = []
    for group in LAUNCHER_GROUPS:
        cells = [t for t in tiles if group_of(t["name"]) == group.key]
        if cells:
            groups.append({"key": group.key, "label": group.label, "cells": cells})
    return groups

# EOF
