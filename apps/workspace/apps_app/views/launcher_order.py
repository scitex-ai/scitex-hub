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
# Operator, 2026-09-14: the FIRST group is the infrastructure everyone uses —
# My Projects, Public Projects, Agents, Cards — and the applications follow:
# Scholar, FigRecipe, Stats, Writer. Then Chat, Settings, Tools, and last Docs,
# App Store, Storage. The Chat and Settings tiles are link tiles
# (services/launcher_links.py), added by the Home + dock redesign the same day.
#
# "stats" holds its slot although no Stats app exists yet (another agent is
# building it): an unregistered name renders nothing, and the day the module
# lands it sorts between FigRecipe and Writer without touching this list. Give
# its manifest "order": 27 (figrecipe is 25, writer 30).
DEFAULT_LAUNCHER_ORDER = [
    # infrastructure
    "home",  # My Projects
    "discovery",  # Public Projects
    "agents",
    "todo",  # Cards
    # applications
    "scholar",
    "figrecipe",
    "stats",  # slot reserved; no app yet
    "writer",
    # chat / settings / tools (console and clew opt out of the grid via
    # show_in_launcher=false, so they never render)
    "chat",  # link tile -> /chat/
    "settings",  # link tile -> /accounts/settings/
    "tools",
    "console",
    "clew",
    # last
    "docs",
    "store",  # App Store
    "storage",
]
_DEFAULT_ORDER_INDEX = {name: i for i, name in enumerate(DEFAULT_LAUNCHER_ORDER)}


def default_order_value(name: str) -> int:
    """Curated launcher position (lower sorts earlier).

    Curated apps occupy 10..120; anything uncurated sorts after them (by
    label). Reorder positions written by api_reorder live at 1000+, well
    clear of both, so an explicit user choice always wins.
    """
    idx = _DEFAULT_ORDER_INDEX.get(name)
    if idx is not None:
        return (idx + 1) * 10
    return 500_000


# EOF
