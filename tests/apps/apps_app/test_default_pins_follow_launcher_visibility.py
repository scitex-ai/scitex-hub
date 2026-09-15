#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Default sidebar pins never lead a user to an app the launcher hides from them.

Card hub-card-required-copy-leftovers-20260914. The pins walk the launcher's
curated order, so they use the grid's own visibility check: an ``internal``
app (Storage today) is not pinned for a non-staff user on a deployment that
has not released internal apps. Cards and Agents are shown to everyone
(operator 2026-09-14 15:48Z; non-staff get an own-scope page), so they stay.
"""

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.views.launcher_pins import default_pinned_module_names

INTERNAL_MODULES = {mod.name for mod in get_all_modules() if mod.visibility == "internal"}
REGISTERED = {mod.name for mod in get_all_modules()}

needs_internal_module = pytest.mark.skipif(
    not INTERNAL_MODULES,
    reason="No internal-visibility app registered (Storage is an optional plugin).",
)


@needs_internal_module
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=False)
def test_non_staff_default_pins_exclude_apps_they_cannot_open():
    # Arrange
    user = User(username="pins-regular", is_staff=False)
    # Act
    pinned = set(default_pinned_module_names(user))
    # Assert
    assert pinned & INTERNAL_MODULES == set()


@needs_internal_module
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=False)
def test_staff_default_pins_keep_internal_apps():
    """Control: the filter is per-user, not a blanket removal."""
    # Arrange
    user = User(username="pins-staff", is_staff=True)
    # Act
    pinned = set(default_pinned_module_names(user))
    # Assert
    assert pinned & INTERNAL_MODULES != set()


@pytest.mark.skipif("agents" not in REGISTERED, reason="Agents plugin not installed")
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=False)
def test_non_staff_default_pins_keep_agents():
    # Arrange
    user = User(username="pins-agents", is_staff=False)
    # Act
    pinned = default_pinned_module_names(user)
    # Assert
    assert "agents" in pinned
