#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guards for the upstream scitex-todo board mount (phase 1: read-only).

Mirrors tests/config/test_writer_mount.py: when the ``scitex_todo``
package is importable, its contract-compliant ``_django`` app must be
installed under the explicit ``ScitexTodoConfig`` path (a bare module
entry falls back to app label ``_django`` and collides with
``figrecipe._django``'s identical fallback) and URL-mounted at
``/todo/``. When the package is absent, neither must appear.

Tenancy (the hub-specific piece) is covered separately in
tests/apps/todo_app/test_tenancy_middleware.py.
"""

from importlib.util import find_spec

import pytest

_TODO_INSTALLED = find_spec("scitex_todo") is not None


@pytest.mark.skipif(not _TODO_INSTALLED, reason="scitex-todo not installed")
def test_todo_app_installed_via_explicit_appconfig_path():
    # Arrange
    from django.conf import settings

    # Act
    entry_present = (
        "scitex_todo._django.apps.ScitexTodoConfig" in settings.INSTALLED_APPS
    )

    # Assert
    assert entry_present is True


@pytest.mark.skipif(not _TODO_INSTALLED, reason="scitex-todo not installed")
def test_todo_root_url_resolves_to_todo_namespace():
    # Arrange
    from django.urls import resolve

    # Act
    match = resolve("/todo/")

    # Assert
    assert match.view_name.startswith("scitex_todo:")


@pytest.mark.skipif(not _TODO_INSTALLED, reason="scitex-todo not installed")
def test_todo_lane_globs_disabled_for_tenancy():
    # Arrange
    import os

    # Act — settings_shared.py must have opted the board out of host-side
    # per-project lane discovery (the union would leak host lanes to
    # every hub user).
    value = os.environ.get("SCITEX_TODO_LANE_GLOBS")

    # Assert
    assert value == ""


@pytest.mark.skipif(_TODO_INSTALLED, reason="scitex-todo is installed")
def test_todo_url_absent_when_package_missing():
    # Arrange
    from django.urls import Resolver404, resolve

    # Act
    try:
        resolve("/todo/")
        resolved = True
    except Resolver404:
        resolved = False

    # Assert
    assert resolved is False
