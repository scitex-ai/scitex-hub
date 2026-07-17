#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guards for the upstream scitex-todo board mount (phase 1: read-only).

Mirrors tests/config/test_writer_mount.py: when the ``scitex_todo``
package is importable, its contract-compliant ``_django`` app must be
installed under the explicit ``ScitexTodoConfig`` path (a bare module
entry falls back to app label ``_django`` and collides with
``figrecipe._django``'s identical fallback) and URL-mounted at
``/apps/cards/`` (the Cards rebrand; /apps/todo/ 301-redirects there).
When the package is absent, neither must appear.

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
def test_cards_root_url_resolves_to_todo_namespace():
    # Arrange
    from django.urls import resolve

    # Act
    match = resolve("/apps/cards/")

    # Assert
    assert match.view_name.startswith("scitex_todo:")


@pytest.mark.skipif(not _TODO_INSTALLED, reason="scitex-todo not installed")
def test_legacy_todo_path_redirects_to_cards():
    # Arrange — old links and pinned tiles must keep working after the
    # Cards rebrand, subpath and query string included.
    from django.test import Client

    # Act
    resp = Client().get("/apps/todo/board/?lane=open", follow=False)

    # Assert
    assert (resp.status_code, resp["Location"]) == (
        301,
        "/apps/cards/board/?lane=open",
    )


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
def test_cards_url_absent_when_package_missing():
    # Arrange — with the package absent the /apps/cards/ mount must not
    # exist. NOTE: resolve() may still MATCH something (catch-all routes
    # swallow unmounted paths — same as /writer/), so the contract here
    # is "does not resolve into the scitex_todo namespace", never a bare
    # Resolver404.
    from django.urls import Resolver404, resolve

    # Act
    try:
        view_name = resolve("/apps/cards/").view_name
    except Resolver404:
        view_name = ""

    # Assert
    assert not view_name.startswith("scitex_todo:")
