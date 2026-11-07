#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guards for the Cards board mount — now a generic plugin mount.

The board is served EXCLUSIVELY through the generic plugin mount
(``plugin_urlpatterns`` + ``PluginMountGuardMiddleware``) from the leaf's
own urlconf and manifest. There is no hub-side mount code left to pin, so
this file pins the CONTRACT instead:

- /apps/cards/ resolves to the leaf namespace when the package is
  installed (a missing optional package skips those tests with a reason);
- the legacy /apps/todo/ subtree still 301-redirects (hub-owned, runs
  everywhere);
- mounting the board still disables host-side lane discovery under the
  env name the package READS (``_optional_apps`` side effect).

Per-user scoping (no cross-user rows) is enforced by the generic
mount-policy guard and covered in
``tests/apps/apps_app/test_plugin_mount_guards.py`` — nothing here names
a store, a lane, or a user.
"""

from __future__ import annotations

import pytest
from django.test import Client

from config.settings._optional_apps import CARDS_APPCONFIG_NAMES


def test_legacy_todo_path_redirects_to_cards():
    # Arrange — old links and pinned tiles must keep working after the
    # Cards rebrand, subpath and query string included.
    # Act
    resp = Client().get("/apps/todo/board/?lane=open", follow=False)

    # Assert
    assert (resp.status_code, resp["Location"]) == (
        301,
        "/apps/cards/board/?lane=open",
    )


def test_cards_root_url_resolves_to_the_leaf_namespace():
    # Arrange — the leaf package must be installed for its mount to exist.
    pytest.importorskip("scitex_cards._django.urls", reason="scitex-cards not installed")
    from django.urls import resolve

    # Act
    match = resolve("/apps/cards/")

    # Assert — the generic mount serves the LEAF's own urlconf (its
    # namespace), never a hub wrapper.
    assert match.view_name.startswith("scitex_cards:")


def test_cards_app_installed_via_explicit_appconfig_path():
    # Arrange — a bare "scitex_cards._django" entry falls back to app label
    # "_django" and collides with figrecipe._django's identical fallback.
    pytest.importorskip("scitex_cards._django.apps", reason="scitex-cards not installed")
    from django.conf import settings

    # Act
    expected = {f"scitex_cards._django.apps.{n}" for n in CARDS_APPCONFIG_NAMES}
    matched = expected & set(settings.INSTALLED_APPS)

    # Assert
    assert len(matched) == 1, (
        f"expected exactly one of {sorted(expected)} in INSTALLED_APPS, "
        f"found {sorted(matched)}"
    )


def test_cards_url_absent_when_package_missing():
    # Arrange — with the package absent the /apps/cards/ mount must not
    # exist. NOTE: resolve() may still MATCH something (catch-all routes
    # swallow unmounted paths), so the contract here is "does not resolve
    # into the leaf namespace", never a bare Resolver404.
    from django.urls import Resolver404, resolve

    try:
        from importlib.util import find_spec

        installed = find_spec("scitex_cards._django.urls") is not None
    except (ImportError, ValueError):
        installed = False
    if installed:
        pytest.skip("scitex-cards is installed; the mount must exist")

    # Act
    try:
        view_name = resolve("/apps/cards/").view_name
    except Resolver404:
        view_name = ""

    # Assert
    assert not view_name.startswith("scitex_cards:")


def test_lane_globs_disabled_for_tenancy_under_the_name_the_package_READS():
    """The opt-out must be set under the env name the CONSUMER reads.

    The union would leak host lanes to every hub user. ``_discover_lanes``
    falls back to ``DEFAULT_LANE_GLOBS`` (per-project lanes) when the
    variable is UNSET, and an explicitly-empty value is the documented
    opt-out — so "unset" and "set to empty" are opposite behaviours here.
    The name is imported from the package, never a literal.
    """
    # Arrange — the consumer's own constant, never a literal.
    import os

    services = pytest.importorskip(
        "scitex_cards._django.services", reason="scitex-cards not installed"
    )

    # Act
    value = os.environ.get(services.ENV_LANE_GLOBS)

    # Assert
    assert value == "", (
        f"{services.ENV_LANE_GLOBS} is {value!r}; it must be the empty string. Unset "
        "means _discover_lanes falls back to DEFAULT_LANE_GLOBS and unions "
        "every per-project lane on the host into the board."
    )


def test_the_retired_lane_globs_name_is_not_what_we_rely_on():
    """Negative control: the old name must not be the ONLY thing exported.

    Without this, restoring the bug (setting only the retired name) would
    leave the suite green as soon as someone re-pins the test above to a
    literal. Pairing them means the suite fails if the export ever drifts
    back off the consumer's name.
    """
    # Arrange
    import os

    services = pytest.importorskip(
        "scitex_cards._django.services", reason="scitex-cards not installed"
    )

    # CAPTURE FIRST, then assert on the local. Asserting directly on
    # `os.environ.get(...)` makes pytest expand os.environ in the failure
    # report — the whole environment, tokens included, into the CI log.
    # Observed while writing this test: the first run printed GH_TOKEN and
    # SAC_LISTEN_BEARER before a hook redacted them.
    value = os.environ.get(services.ENV_LANE_GLOBS)

    # Assert — whatever the retired name holds, the canonical one decides.
    assert services.ENV_LANE_GLOBS != "SCITEX_TODO_LANE_GLOBS", (
        "upstream now reads the retired name; this guard is obsolete"
    )
    assert value == "", (
        "the opt-out is not set under "
        f"{services.ENV_LANE_GLOBS}, the name the package reads (got {value!r})"
    )
