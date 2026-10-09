#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDK shell bridge registration + adapter (card hub-sdk-ui-shell-bridge-20261007).

The Hub renders leaf pages on its own `global_base.html`; the SDK ships
`scitex_sdk/app/app_shell.html` + `scitex_sdk/ui/standalone_shell.html`.
The bridge is registration (settings) + one adapter template mapping the
Hub block vocabulary (`content`) onto the SDK shell (`app_content`).

Pure source-shape tests: no DB, no Django setup, no installed SDK needed —
they read the repo files, so they fail only when the bridge itself drifts.
One assertion per test (STX-TQ007).
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OPTIONAL_APPS = REPO / "config/settings/_optional_apps.py"
BRIDGE = REPO / "templates/shared/sdk_shell_bridge.html"


def test_sdk_app_registered_for_template_resolution():
    # Arrange
    # Act
    src = OPTIONAL_APPS.read_text()
    # Assert
    assert '"scitex_sdk.app"' in src


def test_sdk_ui_registered_for_template_resolution():
    # Arrange
    # Act
    src = OPTIONAL_APPS.read_text()
    # Assert
    assert '"scitex_sdk.ui"' in src


def test_bridge_extends_the_sdk_app_shell():
    # Arrange
    # Act
    src = BRIDGE.read_text()
    # Assert
    assert 'extends "scitex_sdk/app/app_shell.html"' in src


def test_bridge_maps_hub_content_onto_app_content():
    # Arrange
    # Act
    src = BRIDGE.read_text()
    # Assert
    assert "block app_content" in src


def test_bridge_exposes_a_leaf_block():
    # Arrange
    # Act
    src = BRIDGE.read_text()
    # Assert
    assert "hub_leaf_content" in src
