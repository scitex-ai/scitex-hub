"""The generic plugin mount: leaf-declared routes, a version floor, one log line.

``plugin_urlpatterns`` mounts every ``scitex.apps`` leaf at its manifest
route without naming any of its routes. These pin the host rules around
that:

* a hub pattern at the SAME route takes it (the leaf is skipped), while a
  hub pattern nested UNDER it (a dev-only old-direct reference) is hoisted
  ahead of the leaf mount instead of blocking it;
* a leaf below the hub's own declared dependency floor is refused;
* a leaf whose ``mount_policy`` the SDK validator rejects is refused;
* the outcome is ONE INFO summary, never an ERROR per route.

No database, no mocks: the version check runs against real installed
distributions (django, pytest) and the mount runs against the real
installed plugins.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from django.urls import path
from packaging.specifiers import SpecifierSet

pytest.importorskip(
    "scitex_sdk.app.plugins", reason="released scitex-sdk has no plugin API"
)

from apps.workspace.apps_app.services.plugin_apps import (  # noqa: E402
    _hub_subroutes,
    _policy_error,
    _route_taken,
    _version_incompatibility,
    plugin_urlpatterns,
)

LOGGER = "apps.workspace.apps_app.services.plugin_apps"


def _view(request):
    return None


def _leaf(pip_package, **manifest):
    return SimpleNamespace(
        name="leaf_pkg._django",
        label="leaf",
        manifest={"pip_package": pip_package, **manifest},
    )


def _writer_config():
    from scitex_sdk.app.plugins import loaded_plugin_configs

    for config in loaded_plugin_configs():
        if (config.manifest or {}).get("pip_package") == "scitex-writer":
            return config
    pytest.skip("scitex-writer is not installed as a plugin here")


# -- route ownership -------------------------------------------------------


def test_a_hub_pattern_at_the_same_route_takes_it():
    # Arrange
    existing = [path("apps/demo/", _view)]
    # Act
    taken = _route_taken("apps/demo/", existing)
    # Assert
    assert taken is True


def test_a_hub_subroute_does_not_take_the_plugin_route():
    # Arrange
    existing = [path("apps/demo/old-direct/", _view)]
    # Act
    taken = _route_taken("apps/demo/", existing)
    # Assert
    assert taken is False


def test_a_hub_subroute_is_reported_for_hoisting():
    # Arrange
    sub = path("apps/demo/old-direct/", _view)
    existing = [path("apps/other/", _view), sub]
    # Act
    found = _hub_subroutes("apps/demo/", existing)
    # Assert
    assert found == [sub]


def test_old_direct_subroute_is_hoisted_ahead_of_the_leaf_mount():
    # Arrange — the real installed writer leaf, mounted with a hub sub-route
    config = _writer_config()
    sub = path("apps/writer/old-direct/", _view)
    existing = [sub]
    # Act
    mounted = plugin_urlpatterns(existing)
    routes = [str(p.pattern) for p in mounted]
    # Assert — moved out of the hub list, listed right before the leaf mount
    assert (existing, routes.index("apps/writer/old-direct/") + 1) == (
        [],
        routes.index(f"apps/{config.manifest['slug']}/"),
    )


# -- version floor -----------------------------------------------------------


def test_leaf_below_the_hub_floor_is_refused():
    # Arrange — a real installed distribution against an unreachable floor
    config = _leaf("django")
    # Act
    reason = _version_incompatibility(config, {"django": SpecifierSet(">=9999")})
    # Assert
    assert "does not satisfy" in reason


def test_leaf_at_or_above_the_hub_floor_is_admitted():
    # Arrange
    config = _leaf("django")
    # Act
    reason = _version_incompatibility(config, {"django": SpecifierSet(">=1")})
    # Assert
    assert reason is None


def test_leaf_without_a_hub_floor_is_not_checked():
    # Arrange
    config = _leaf("pytest")
    # Act
    reason = _version_incompatibility(config, {"django": SpecifierSet(">=9999")})
    # Assert
    assert reason is None


def test_floor_for_a_missing_distribution_is_refused():
    # Arrange
    config = _leaf("no-such-distribution-xyz")
    # Act
    reason = _version_incompatibility(
        config, {"no-such-distribution-xyz": SpecifierSet(">=1")}
    )
    # Assert
    assert "no installed distribution" in reason


def test_installed_writer_satisfies_the_hub_floor():
    # Arrange — the hub's own pyproject floor, read from installed metadata
    from apps.workspace.apps_app.services.plugin_apps import _hub_requirements

    config = _writer_config()
    # Act
    reason = _version_incompatibility(config, _hub_requirements())
    # Assert
    assert reason is None


# -- SDK mount_policy validator --------------------------------------------------


def test_file_touching_leaf_without_a_jail_is_refused():
    # Arrange
    config = _leaf("django", mount_policy={"touches_files": True})
    # Act
    reason = _policy_error(config)
    # Assert
    assert "invalid mount_policy" in reason


def test_login_only_policy_is_admitted():
    # Arrange
    config = _leaf("django", mount_policy={"login_required": True})
    # Act
    reason = _policy_error(config)
    # Assert
    assert reason is None


# -- logging ---------------------------------------------------------------------


def test_mount_logs_one_info_summary(caplog):
    # Arrange
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    # Act
    plugin_urlpatterns([])
    records = [r for r in caplog.records if r.name == LOGGER]
    # Assert
    assert [r.levelno for r in records] == [logging.INFO]


def test_mount_summary_names_the_writer_leaf(caplog):
    # Arrange
    _writer_config()
    caplog.set_level(logging.INFO, logger=LOGGER)
    # Act
    plugin_urlpatterns([])
    # Assert
    assert "writer" in caplog.records[-1].getMessage()
