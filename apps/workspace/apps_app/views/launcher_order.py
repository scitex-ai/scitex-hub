#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Curated default launcher order — the one list every launcher surface sorts by.

Extracted from ``launcher.py`` so the workspace grid, the sidebar default pins
and the global-header AppLauncher (``config.context_processors``) can share it
without importing the whole launcher view module.
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
# Operator, 2026-09-14: the FIRST row is the infrastructure everyone uses —
# My Projects, Public Projects, Agents, Cards — and the research row follows:
# Scholar, FigRecipe, Stats, Writer. Stats has no launcher app yet; when it
# lands, insert its module name between "figrecipe" and "writer" here and give
# its manifest "order": 27 (figrecipe is 25, writer 30). Then a settings/other
# row (Tools, and Console/Clew if they are ever shown), and last Docs, App
# Store, Storage (operator, 2026-09-14 10:49Z).
DEFAULT_LAUNCHER_ORDER = [
    # infrastructure row
    "home",  # My Projects
    "discovery",  # Public Projects
    "agents",
    "todo",  # Cards
    # research row
    "scholar",
    "figrecipe",
    "writer",
    # settings / other row (console and clew are opted out of the grid via
    # show_in_launcher=false, so only Tools shows today)
    "tools",
    "console",
    "clew",
    # last row
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
