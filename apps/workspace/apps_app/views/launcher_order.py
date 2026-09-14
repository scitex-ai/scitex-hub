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
#   FOUNDATION (基盤): My Projects, Public Projects, Agents, Cards, Storage
#   WORK (作業):       Scholar, FigRecipe, Stats (reserved), Writer, Chat, Tools
#   SYSTEM (システム): Settings, Docs, App Store
# Within a group the order is the operator's earlier order (infrastructure,
# then Scholar-FigRecipe-Stats-Writer, then Chat/Settings/Tools, then
# Docs/App Store/Storage). Each group carries role="group" and a translated
# aria-label, which launcher/grid.css also shows as the band's visible label.
#
# "stats" holds its slot although no Stats app exists yet (another agent is
# building it): its cell stays empty, and the day the module lands it fills
# that cell without touching this list. Give its manifest "order": 27
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
        ("home", "discovery", "agents", "todo", "storage"),
    ),
    LauncherGroup(
        "work",
        "Work",
        (
            "scholar",
            "figrecipe",
            "stats",  # reserved slot; no app yet
            "writer",
            "chat",  # link tile -> /chat/
            "tools",
            "console",
            "clew",
        ),
    ),
    LauncherGroup(
        "system",
        "System",
        ("settings", "docs", "store"),  # settings = link tile; store = App Store
    ),
)

#: Uncurated apps (community store apps, dev installs) are applications.
DEFAULT_GROUP = "work"

#: Cells a group keeps even when the app is not installed yet.
RESERVED_SLOTS = frozenset({"stats"})

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
    return 500_000


def group_of(name: str) -> str:
    """The group key an app belongs to."""
    return _GROUP_OF.get(name, DEFAULT_GROUP)


def group_rank(name: str) -> int:
    """Sort rank of an app's group (groups never interleave)."""
    return _GROUP_RANK[group_of(name)]


def group_cells(tiles: list[dict]) -> list[dict]:
    """The tiles as groups of grid cells, in group order.

    ``tiles`` must already be sorted (group first, then position). Returns
    ``[{"key", "label", "cells"}]``; a reserved slot whose app is not present
    becomes an empty cell ``{"is_slot": True, "slot": name}`` at its position,
    so the apps after it keep their columns. A group with no tiles is omitted.
    """
    present = {tile["name"] for tile in tiles}
    groups = []
    for group in LAUNCHER_GROUPS:
        members = [t for t in tiles if group_of(t["name"]) == group.key]
        if not members:
            continue
        cells: list[dict] = []
        # A group the user has drag-reordered keeps THEIR order, without the
        # reserved gap (it would land somewhere they did not put it).
        curated = not any(t.get("user_ordered") for t in members)
        for tile in members:
            if curated and tile["name"] in _DEFAULT_ORDER_INDEX:
                before = group.members[: group.members.index(tile["name"])]
                for name in before:
                    held = any(c.get("slot") == name for c in cells)
                    if name in RESERVED_SLOTS and name not in present and not held:
                        cells.append({"is_slot": True, "slot": name})
            cells.append(tile)
        groups.append({"key": group.key, "label": group.label, "cells": cells})
    return groups

# EOF
