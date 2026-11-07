"""Plugin label collisions use real declarations and preserve host app owners.

Settings now reads declared AppConfig metadata without executing class bodies.
These controls retain the original same-package replacement, collision and
actual Clew regression through the current host merge contract. The unresolvable
case must be skipped explicitly, rather than admitting an unprovable app.
"""

from __future__ import annotations

import importlib
import sys
import uuid

import pytest
from scitex_sdk.app.plugins import PluginApp

from config.settings._optional_apps import (
    _entry_claimed_labels,
    _with_host_plugin_apps,
)


@pytest.fixture
def declared_apps(tmp_path):
    """Create actual Python package declarations, without substituted modules."""
    names = []
    sys.path.insert(0, str(tmp_path))

    def create(label):
        name = "collision_" + uuid.uuid4().hex
        names.append(name)
        root = tmp_path / name
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "apps.py").write_text(
            "from django.apps import AppConfig\n"
            "class DeclaredConfig(AppConfig):\n"
            f"    name = {name!r}\n"
            f"    label = {label!r}\n"
        )
        importlib.invalidate_caches()
        return name + ".apps.DeclaredConfig"

    try:
        yield create
    finally:
        sys.path.remove(str(tmp_path))
        for name in names:
            sys.modules.pop(name, None)
            sys.modules.pop(name + ".apps", None)
        importlib.invalidate_caches()


def test_plugin_duplicating_a_local_app_label_is_skipped(declared_apps, caplog):
    # Arrange
    local = declared_apps("owned_clew")
    colliding = declared_apps("owned_clew")
    other = declared_apps("other_app")
    plugins = [PluginApp("clew", colliding), PluginApp("other", other)]
    # Act
    with caplog.at_level("WARNING"):
        entries = _with_host_plugin_apps([], [local], plugins)
    # Assert
    assert entries == [other] and any(
        "clew" in record.message for record in caplog.records
    )


def test_plugin_replacing_its_same_package_entry_is_kept(declared_apps):
    # Arrange
    entry = declared_apps("figure_label")
    # Act
    entries = _with_host_plugin_apps([entry], (), [PluginApp("figure", entry)])
    # Assert
    assert entries == [entry]


def test_plugin_with_unresolvable_label_is_skipped(declared_apps, caplog):
    # Arrange
    local = declared_apps("retained_local")
    ghost = PluginApp("ghost", "absent_plugin.apps.GhostConfig")
    # Act
    with caplog.at_level("WARNING"):
        entries = _with_host_plugin_apps([local], (), [ghost])
    # Assert
    assert entries == [local] and any(
        "ghost" in record.message for record in caplog.records
    )


def test_real_clew_pair_skips_the_plugin():
    # Arrange
    local = "apps.workspace.clew_app"
    plugin = PluginApp("clew", "scitex_clew._django.apps.ClewAppConfig")
    # Act
    entries = _with_host_plugin_apps([], [local], [plugin])
    # Assert
    assert entries == [] and _entry_claimed_labels(local) == {"clew_app"}
