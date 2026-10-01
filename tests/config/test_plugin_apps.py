"""``pip install <pkg>`` with a ``scitex.apps`` entry point makes a hub app."""

from __future__ import annotations

from types import SimpleNamespace

from django.urls import path
from scitex_sdk.app.plugins import PluginApp

from apps.workspace.apps_app.services.plugin_apps import (
    _route_taken,
    plugin_module_config,
)
from config.settings._optional_apps import with_plugin_apps


def _view(request):
    return None


def test_plugin_replaces_hand_written_writer_entry():
    # Arrange
    # Writer is a required installed leaf; optional FigRecipe is not a test prerequisite.
    plugins = [PluginApp("writer", "scitex_writer._django.apps.WriterEditorConfig")]
    # Act
    merged = with_plugin_apps(["scitex_sdk.ui", "scitex_writer._django"], plugins)
    # Assert
    assert merged == ["scitex_sdk.ui", "scitex_writer._django.apps.WriterEditorConfig"]


def test_plugin_with_missing_module_is_skipped():
    # Arrange
    plugins = [PluginApp("ghost", "no_such_pkg_xyz.apps.GhostConfig")]
    # Act
    merged = with_plugin_apps(["scitex_sdk.ui"], plugins)
    # Assert
    assert merged == ["scitex_sdk.ui"]


def test_route_the_hub_serves_is_not_remounted():
    # Arrange
    existing = [path("apps/figrecipe/", _view)]
    # Act
    taken = _route_taken("apps/figrecipe/", existing)
    # Assert
    assert taken


def test_new_route_is_free():
    # Arrange
    existing = [path("apps/figrecipe/", _view)]
    # Act
    taken = _route_taken("apps/hello-world/", existing)
    # Assert
    assert not taken


def test_tile_comes_from_the_plugin_manifest():
    # Arrange
    config = SimpleNamespace(
        name="hello_world",
        label="hello_world",
        manifest={"slug": "hello-world", "label": "Hello World", "icon": "fas fa-x"},
    )
    # Act
    module = plugin_module_config(config)
    # Assert
    assert (module.name, module.label, module.get_url()) == (
        "hello-world",
        "Hello World",
        "/apps/hello-world/",
    )
