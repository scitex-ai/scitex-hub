#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_console_is_hidden_from_the_launcher.py
"""Console is hidden from the launcher, and still reachable at /console/.

OPERATOR, Telegram 4794, 2026-09-05: 「コンソールっていうのがちょっと難しいので
1階隠してみます。私もどうやって使ってるのかよくわからなくて」— Console is a bit
hard, so hide it one level; he is not sure how he uses it himself. So this is
HIDE, not remove: the app keeps working for anyone who navigates to it, and the
route is asserted below precisely so a later reader does not "finish the job"
by deleting it.

HIDING IT TAKES TWO SURFACES, NOT ONE
-------------------------------------
``show_in_launcher: false`` drops the grid tile. It does NOT drop the sidebar
pin: ``default_pinned_module_names()`` walked ``DEFAULT_LAUNCHER_ORDER`` and
took the first ``MAX_PINNED_MODULES`` (5) registered names, and Console sat
fifth — so the tile would have vanished while the pin stayed, leaving Console
in the sidebar of a user who had been told it was gone. That function now skips
any module that opted out of the grid, which is the same one flag governing
both surfaces. Clew and Comms already declared that flag and are excluded for
the same reason.
"""

import json
from pathlib import Path

import pytest
from django.urls import resolve

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.views.launcher import (
    DEFAULT_LAUNCHER_ORDER,
    MAX_PINNED_MODULES,
    default_pinned_module_names,
)

# tests/apps/apps_app/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONSOLE_MANIFEST = (
    _REPO_ROOT / "apps" / "workspace" / "console_app" / "manifest.json"
)


def test_the_console_manifest_opts_out_of_the_launcher():
    # Arrange
    manifest = json.loads(_CONSOLE_MANIFEST.read_text())
    # Act
    opted_out = manifest.get("show_in_launcher")
    # Assert
    assert opted_out is False, (
        "console_app/manifest.json must declare show_in_launcher: false "
        f"(it declares {opted_out!r})"
    )


def test_the_registry_carries_that_flag_through():
    """Control for the test above: the file is only worth anything if read."""
    # Arrange
    modules = {module.name: module for module in get_all_modules()}
    # Act
    console = modules.get("console")
    # Assert
    assert console is not None and console.show_in_launcher is False


def test_console_is_not_in_the_default_sidebar_pins():
    """The half of the hide that show_in_launcher alone would have missed."""
    # Arrange
    curated_position = DEFAULT_LAUNCHER_ORDER.index("console")
    # Act
    pinned = default_pinned_module_names()
    # Assert
    assert "console" not in pinned, (
        f"console sits at curated position {curated_position} and "
        f"MAX_PINNED_MODULES is {MAX_PINNED_MODULES}, so it is pinned: {pinned}"
    )


def test_the_pin_set_is_still_full():
    """Dropping Console must promote the next app, not shrink the sidebar."""
    # Arrange
    grid_apps = [m.name for m in get_all_modules() if m.show_in_launcher]
    # Act
    pinned = default_pinned_module_names()
    # Assert
    assert len(pinned) == min(MAX_PINNED_MODULES, len(grid_apps) - 1)


def test_every_pinned_app_actually_has_a_tile():
    """The invariant behind the change: no pin without a grid tile."""
    # Arrange
    grid_apps = {m.name for m in get_all_modules() if m.show_in_launcher}
    # Act
    orphans = [name for name in default_pinned_module_names() if name not in grid_apps]
    # Assert
    assert orphans == [], f"pinned but absent from the grid: {orphans}"


def test_console_is_still_reachable_at_its_own_url():
    """HIDE, not remove. Deleting the route would break the app for real."""
    # Arrange
    url = "/apps/console/"
    # Act
    match = resolve(url)
    # Assert
    assert match is not None and match.app_name == "console_app"


@pytest.mark.django_db
def test_console_renders_no_launcher_tile(client, django_user_model):
    """The surface itself, not just the flag that feeds it."""
    # Arrange
    user = django_user_model.objects.create_user(
        username="console-hide-probe", password="x"
    )
    client.force_login(user)
    # Act
    tiles = {tile["name"] for tile in client.get("/").context["tiles"]}
    # Assert
    assert "console" not in tiles, f"console still tiled among {sorted(tiles)}"


# EOF
