#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_app_order_is_the_operators_order.py
"""The three research apps appear in the order the operator asked for.

OPERATOR, Telegram 4794, 2026-09-05: 「順番はスカラフィグレシピライター」 — the
launcher should read Scholar, then FigRecipe, then Writer.

WHAT DECIDES THE ORDER A USER SEES
----------------------------------
``DEFAULT_LAUNCHER_ORDER`` in ``apps_app/views/launcher.py`` — NOT the
manifests. ``_build_tiles`` enumerates ``get_all_modules()`` (which sorts on
the manifest ``order``) and then re-sorts every tile through
``_default_order_value()``, which reads the curated list. So a manifest edit
alone moves nothing on the grid.

That is not a guess: the first attempt at this card changed only the three
manifests, and CI (all three Python legs, identically) reported the launcher
still listing ``('writer', 'scholar', 'figrecipe')``. Both are changed here,
and both are asserted below, because leaving the two sources to disagree is
what made this easy to get wrong in the first place.

THE THREE LAYERS, ASSERTED SEPARATELY ON PURPOSE
------------------------------------------------
1. the manifest FILES on disk (pure JSON — no Django, no import machinery)
2. the REGISTRY's view of them (``get_all_modules()``)
3. the CURATED list the grid actually sorts by

Layer 1 is the control for layer 2. On this host layers 1 and 2 agree
(measured 2026-09-05: the registry reports scholar 20, figrecipe 25,
writer 30) while CI's layer 2 disagreed — so if that splits again, layer 1
passing and layer 2 failing pins it as a registry-LOADING problem rather
than a data problem, and the failure message carries the table needed to
say which.
"""

import json
from pathlib import Path

import pytest

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.views.launcher import DEFAULT_LAUNCHER_ORDER

RESEARCH_APPS = ("scholar", "figrecipe", "writer")

# tests/apps/apps_app/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFESTS = {
    name: _REPO_ROOT / "apps" / "workspace" / f"{name}_app" / "manifest.json"
    for name in RESEARCH_APPS
}


# ---------------------------------------------------------------------------
# Layer 1 — the manifest files themselves (the control)
# ---------------------------------------------------------------------------
def test_every_research_manifest_is_actually_on_disk():
    """Control: a missing file would make the order assertions vacuous."""
    # Arrange
    paths = dict(_MANIFESTS)
    # Act
    missing = [name for name, path in paths.items() if not path.is_file()]
    # Assert
    assert missing == [], f"no manifest.json for {missing}"


def test_the_manifest_files_declare_scholar_figrecipe_writer():
    # Arrange
    orders = {
        name: json.loads(path.read_text())["order"]
        for name, path in _MANIFESTS.items()
    }
    # Act
    by_order = tuple(sorted(orders, key=lambda n: orders[n]))
    # Assert
    assert by_order == RESEARCH_APPS, f"manifests declare {orders}"


# ---------------------------------------------------------------------------
# Layer 2 — what the registry makes of those files
# ---------------------------------------------------------------------------
@pytest.fixture(name="registry_table")
def _registry_table():
    """(name, order) for every registered module, in registry order."""
    return [(module.name, module.order) for module in get_all_modules()]


def test_the_registry_reads_the_order_the_manifests_declare(registry_table):
    """Layer 2 against layer 1. A split here is a LOADING fault, not data."""
    # Arrange
    seen = {name: order for name, order in registry_table if name in RESEARCH_APPS}
    declared = {
        name: json.loads(path.read_text())["order"]
        for name, path in _MANIFESTS.items()
    }
    # Act
    disagreements = {
        name: (declared[name], seen.get(name))
        for name in RESEARCH_APPS
        if seen.get(name) != declared[name]
    }
    # Assert
    assert disagreements == {}, (
        "the registry disagrees with the manifest files it reads "
        f"{{name: (on disk, in registry)}} = {disagreements}. "
        f"Full registry table: {registry_table}"
    )


# ---------------------------------------------------------------------------
# Layer 3 — the curated list the launcher grid actually sorts by
# ---------------------------------------------------------------------------
def test_the_curated_launcher_order_reads_scholar_figrecipe_writer():
    """This is the one a user sees; _default_order_value() reads this list."""
    # Arrange
    present = [name for name in DEFAULT_LAUNCHER_ORDER if name in RESEARCH_APPS]
    # Act
    sequence = tuple(present)
    # Assert
    assert sequence == RESEARCH_APPS, (
        f"the launcher grid lists {sequence}; the operator asked for "
        f"{RESEARCH_APPS} (Telegram 4794, 2026-09-05)"
    )


def test_scholar_comes_before_writer_on_the_grid():
    """The single reversal that motivated the change: Writer used to lead."""
    # Arrange
    positions = {name: i for i, name in enumerate(DEFAULT_LAUNCHER_ORDER)}
    # Act
    scholar_first = positions["scholar"] < positions["writer"]
    # Assert
    assert scholar_first is True


def test_no_other_app_sits_between_scholar_and_writer_on_the_grid():
    """Console used to split the three apart; they must read as one group."""
    # Arrange
    positions = {name: i for i, name in enumerate(DEFAULT_LAUNCHER_ORDER)}
    span = DEFAULT_LAUNCHER_ORDER[positions["scholar"] : positions["writer"] + 1]
    # Act
    intruders = [name for name in span if name not in RESEARCH_APPS]
    # Assert
    assert intruders == [], f"{intruders} sit between Scholar and Writer"


def test_console_still_follows_the_research_apps():
    """Hiding Console is a separate card; here it must simply not lead."""
    # Arrange
    positions = {name: i for i, name in enumerate(DEFAULT_LAUNCHER_ORDER)}
    # Act
    after = positions["console"] > positions["writer"]
    # Assert
    assert after is True


# EOF
