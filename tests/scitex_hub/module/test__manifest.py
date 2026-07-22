#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_hub.module._manifest (ModuleManifest validation)."""

from __future__ import annotations

import pytest

from scitex_hub.module._manifest import VALID_CATEGORIES, ModuleManifest


def test_default_category_is_valid():
    # Arrange
    name = "demo"
    # Act
    manifest = ModuleManifest(name=name)
    # Assert
    assert manifest.category in VALID_CATEGORIES


def test_invalid_category_raises_value_error():
    # Arrange
    bad_category = "not-a-category"
    # Act
    construct = lambda: ModuleManifest(name="demo", category=bad_category)  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        construct()


def test_to_dict_round_trips_name():
    # Arrange
    manifest = ModuleManifest(name="demo", label="Demo", category="analysis")
    # Act
    payload = manifest.to_dict()
    # Assert
    assert payload["name"] == "demo"


def test_to_dict_preserves_category():
    # Arrange
    manifest = ModuleManifest(name="demo", category="visualization")
    # Act
    payload = manifest.to_dict()
    # Assert
    assert payload["category"] == "visualization"


# EOF
