#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_app_order_is_the_operators_order.py
"""The three research apps appear in the order the operator asked for.

OPERATOR, Telegram 4794, 2026-09-05: 「順番はスカラフィグレシピライター」 — the
launcher should read Scholar, then FigRecipe, then Writer. Before this, the
manifests ordered them Writer (20), Scholar (30), FigRecipe (45), with Console
(40) sitting between Scholar and FigRecipe.

The order is DATA, not code: ``registry.get_all_modules()`` sorts on the
``order`` integer each app's manifest.json declares, so this file asserts the
resulting sequence rather than the three literals — a test that repeated the
numbers would pass while the launcher showed something else, since a fourth
app landing on the same number changes what a user sees and not those numbers.

The sequence is asserted through the registry's own public function, which is
what the launcher view calls.
"""

import pytest

from apps.infra.workspace_app.registry import get_all_modules

RESEARCH_APPS = ("scholar", "figrecipe", "writer")


@pytest.fixture(name="ordered_names")
def _ordered_names():
    """Every registered module name, in the order the launcher renders them."""
    return [module.name for module in get_all_modules()]


def test_the_three_research_apps_read_scholar_figrecipe_writer(ordered_names):
    # Arrange — keep only the three the operator named, in registry order.
    present = [name for name in ordered_names if name in RESEARCH_APPS]
    # Act
    sequence = tuple(present)
    # Assert
    assert sequence == RESEARCH_APPS, (
        f"the launcher lists {sequence}; the operator asked for {RESEARCH_APPS} "
        "(Telegram 4794, 2026-09-05)"
    )


def test_scholar_comes_before_writer(ordered_names):
    """The single reversal that motivated the change: Writer used to be first."""
    # Arrange
    positions = {name: i for i, name in enumerate(ordered_names)}
    # Act
    scholar_first = positions["scholar"] < positions["writer"]
    # Assert
    assert scholar_first is True


def test_no_other_app_sits_between_scholar_and_writer(ordered_names):
    """Console used to split the three apart; the group must read as a group."""
    # Arrange
    positions = {name: i for i, name in enumerate(ordered_names)}
    span = ordered_names[positions["scholar"] : positions["writer"] + 1]
    # Act
    intruders = [name for name in span if name not in RESEARCH_APPS]
    # Assert
    assert intruders == [], f"{intruders} sit between Scholar and Writer"


# EOF
