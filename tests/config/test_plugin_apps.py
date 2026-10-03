"""``pip install <pkg>`` with a ``scitex.apps`` entry point makes a hub app."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.urls import path

pytest.importorskip("scitex_app.plugins", reason="released scitex-app has no plugin API")

from scitex_app.plugins import PluginApp  # type: ignore[import-not-found]

from apps.workspace.apps_app.services.plugin_apps import (
    _route_taken,
    plugin_module_config,
)
from config.settings._optional_apps import with_plugin_apps


def _view(request):
    return None


def test_plugin_replaces_hand_written_figrecipe_entry():
    # Arrange
    plugins = [PluginApp("figrecipe", "figrecipe._django.apps.FigRecipeEditorConfig")]
    # Act
    merged = with_plugin_apps(["scitex_ui", "figrecipe._django"], plugins)
    # Assert
    assert merged == ["scitex_ui", "figrecipe._django.apps.FigRecipeEditorConfig"]


def test_plugin_with_missing_module_is_skipped():
    # Arrange
    plugins = [PluginApp("ghost", "no_such_pkg_xyz.apps.GhostConfig")]
    # Act
    merged = with_plugin_apps(["scitex_ui"], plugins)
    # Assert
    assert merged == ["scitex_ui"]


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


@pytest.fixture
def config_packages(tmp_path):
    """Real importable AppConfigs; transport, models and engines are absent."""
    import sys

    prefix = "plugin_label_ports_" + tmp_path.name.replace("-", "_")
    root = tmp_path / prefix
    root.mkdir()
    (root / "__init__.py").write_text("")
    packages = {}
    for slug, label in (
        ("host", "host_label"),
        ("peer", "peer_label"),
        ("collision", "host_label"),
        ("other_collision", "peer_label"),
    ):
        package = root / slug
        package.mkdir()
        (package / "__init__.py").write_text("")
        module = f"{prefix}.{slug}"
        (package / "apps.py").write_text(
            "from django.apps import AppConfig\n"
            "class DefaultConfig(AppConfig):\n"
            "    default = True\n"
            f"    name = {module!r}\n"
            f"    label = {label!r}\n"
            "class ReplacementConfig(DefaultConfig):\n"
            "    default = False\n"
            "class ChangedLabelConfig(DefaultConfig):\n"
            "    default = False\n"
            "    label = 'changed_label'\n"
            "class OtherOwnedLabelConfig(DefaultConfig):\n"
            "    default = False\n"
            "    label = 'peer_label'\n"
            "not_a_config = object()\n"
        )
        packages[slug] = module
    broken = root / "missing_dependency"
    broken.mkdir()
    (broken / "__init__.py").write_text("")
    (broken / "apps.py").write_text(
        "raise ModuleNotFoundError('optional GUI dependency absent')\n"
    )
    packages["missing_dependency"] = f"{prefix}.missing_dependency"
    sys.path.insert(0, str(tmp_path))
    try:
        yield packages
    finally:
        sys.path.remove(str(tmp_path))
        for name in tuple(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]


def _compose_registered_apps(entries, registered_entries, plugins, django_entries=()):
    """Execute the actual settings assembly boundary without Hub bootstrap."""
    import ast
    from pathlib import Path

    import config.settings._optional_apps as optional

    source = Path(optional.__file__).with_name("settings_shared.py")
    tree = ast.parse(source.read_text())
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id in {"THIRD_PARTY_APPS", "LOCAL_APPS", "INSTALLED_APPS"}
            for target in node.targets
        ):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                if node.value.func.id in {
                    "with_plugin_apps", "_with_host_plugin_apps", "discover_local_apps"
                }:
                    selected.append(node)
            elif any(
                isinstance(target, ast.Name) and target.id == "INSTALLED_APPS"
                for target in node.targets
            ):
                selected.append(node)
    namespace = {
        "THIRD_PARTY_APPS": entries,
        "DJANGO_APPS": list(django_entries),
        "discover_local_apps": lambda: registered_entries,
        "with_plugin_apps": lambda values: optional.with_plugin_apps(values, plugins),
        "_with_host_plugin_apps": lambda values, owners: optional._with_host_plugin_apps(
            values, owners, plugins
        ),
    }
    exec(
        compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return namespace["INSTALLED_APPS"]


def test_existing_label_owner_rejects_a_different_plugin(config_packages, caplog):
    # Arrange
    owner = config_packages["host"]
    plugins = [
        PluginApp("collision", config_packages["collision"] + ".apps.DefaultConfig")
    ]
    # Act
    merged = with_plugin_apps([owner], plugins)
    # Assert
    assert merged == [owner] and "registered app retained" in caplog.text


def test_local_owner_survives_real_django_registry_population(config_packages):
    from django.apps.registry import Apps

    # Arrange
    local = config_packages["host"]
    plugins = [
        PluginApp("collision", config_packages["collision"] + ".apps.DefaultConfig")
    ]
    # Act
    installed = _compose_registered_apps([], [local], plugins)
    registry = Apps(installed_apps=installed)
    # Assert
    assert [
        (config.label, config.name) for config in registry.get_app_configs()
    ] == [("host_label", local)]


def test_noncolliding_plugins_keep_the_existing_host_order(config_packages):
    # Arrange
    local = config_packages["host"]
    peer = config_packages["peer"] + ".apps.DefaultConfig"
    # Act
    installed = _compose_registered_apps([], [local], [PluginApp("peer", peer)])
    # Assert
    assert installed == [peer, local]


def test_same_module_replacement_keeps_its_position(config_packages):
    # Arrange
    first, second = config_packages["host"], config_packages["peer"]
    replacement = first + ".apps.ReplacementConfig"
    # Act
    merged = with_plugin_apps([first, second], [PluginApp("host", replacement)])
    # Assert
    assert merged == [replacement, second]


def test_a_changed_same_module_label_releases_the_old_label(config_packages):
    from django.apps.registry import Apps

    # Arrange
    original = config_packages["host"]
    replacement = original + ".apps.ChangedLabelConfig"
    newcomer = config_packages["collision"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps(
        [original], [PluginApp("replacement", replacement), PluginApp("newcomer", newcomer)]
    )
    registry = Apps(installed_apps=merged)
    # Assert
    assert [
        (config.label, config.name) for config in registry.get_app_configs()
    ] == [("changed_label", original), ("host_label", config_packages["collision"])]


def test_new_plugins_cannot_duplicate_an_accepted_label(config_packages):
    # Arrange
    first = config_packages["peer"] + ".apps.DefaultConfig"
    second = config_packages["other_collision"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps([], [PluginApp("first", first), PluginApp("second", second)])
    # Assert
    assert merged == [first]


def test_a_local_module_is_not_appended_again(config_packages):
    # Arrange
    local = config_packages["host"]
    plugin = PluginApp("host", local + ".apps.DefaultConfig")
    # Act
    installed = _compose_registered_apps([], [local], [plugin])
    # Assert
    assert installed == [local]


def test_a_core_owner_is_reserved_before_optional_plugins(config_packages):
    # Arrange
    core, local = config_packages["host"], config_packages["peer"]
    plugin = PluginApp("collision", config_packages["collision"] + ".apps.DefaultConfig")
    # Act
    installed = _compose_registered_apps([], [local], [plugin], django_entries=[core])
    # Assert
    assert installed == [core, local]


def test_a_local_module_keeps_its_label_when_plugin_metadata_differs(config_packages, caplog):
    # Arrange
    local = config_packages["host"]
    plugin = PluginApp("host", local + ".apps.ChangedLabelConfig")
    # Act
    installed = _compose_registered_apps([], [local], [plugin])
    # Assert
    assert installed == [local] and "already registered elsewhere by the host" in caplog.text


def test_a_replacement_cannot_take_another_existing_label(config_packages):
    # Arrange
    first, second = config_packages["host"], config_packages["peer"]
    plugin = PluginApp("host", first + ".apps.OtherOwnedLabelConfig")
    # Act
    installed = with_plugin_apps([first, second], [plugin])
    # Assert
    assert installed == [first, second]


def test_an_absent_optional_config_preserves_existing_apps(config_packages):
    # Arrange
    owner = config_packages["host"]
    value = "no_such_label_port_xyz.apps.AbsentConfig"
    # Act
    merged = with_plugin_apps([owner], [PluginApp("absent_module", value)])
    # Assert
    assert merged == [owner]


def test_a_missing_optional_dependency_preserves_existing_apps(config_packages):
    # Arrange
    owner = config_packages["host"]
    value = config_packages["missing_dependency"] + ".apps.MissingConfig"
    # Act
    merged = with_plugin_apps([owner], [PluginApp("missing_dependency", value)])
    # Assert
    assert merged == [owner]


def test_invalid_optional_config_metadata_preserves_existing_apps(config_packages):
    # Arrange
    owner = config_packages["host"]
    value = config_packages["peer"] + ".apps.not_a_config"
    # Act
    merged = with_plugin_apps([owner], [PluginApp("invalid_class", value)])
    # Assert
    assert merged == [owner]


def test_no_plugins_preserves_existing_and_local_order(config_packages):
    # Arrange
    third, local = config_packages["peer"], config_packages["host"]
    # Act
    installed = _compose_registered_apps([third], [local], [])
    # Assert
    assert installed == [third, local]


def test_no_plugins_keeps_unavailable_metadata_for_normal_setup():
    # Arrange
    existing = ["no_such_host_app_xyz"]
    # Act
    merged = with_plugin_apps(existing, [])
    # Assert
    assert merged == existing


@pytest.fixture
def alias_config_packages(config_packages, tmp_path):
    """Valid Django config aliases whose merger keys differ from app names."""
    host, peer = config_packages["host"], config_packages["peer"]
    namespace = host.rsplit(".", 1)[0]
    packages = {}
    for slug, label in (("alias_host", "host_label"), ("alias_changed", "different_label")):
        module = namespace + "." + slug
        path = tmp_path / namespace / slug
        path.mkdir()
        (path / "__init__.py").write_text("")
        (path / "apps.py").write_text(
            "from django.apps import AppConfig\n"
            "class DefaultConfig(AppConfig):\n"
            "    default = True\n"
            f"    name = {host!r}\n"
            f"    label = {label!r}\n"
            "class ReplacementConfig(DefaultConfig):\n"
            "    default = False\n"
            "    label = 'replacement_label'\n"
            "class MovedConfig(DefaultConfig):\n"
            "    default = False\n"
            f"    name = {peer!r}\n"
            "    label = 'moved_label'\n"
        )
        packages[slug] = module
    return packages


def _registry_metadata(installed):
    from django.apps.registry import Apps

    return [
        (config.name, config.label)
        for config in Apps(installed_apps=installed).get_app_configs()
    ]


def test_a_config_alias_cannot_append_an_existing_real_name(config_packages, alias_config_packages, caplog):
    # Arrange
    host = config_packages["host"]
    alias = alias_config_packages["alias_host"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps([host], [PluginApp("alias", alias)])
    observed = _registry_metadata(merged)
    # Assert
    assert (
        merged == [host] and observed == [(host, "host_label")]
        and "duplicate app name" in caplog.text
    )


def test_two_aliases_with_distinct_labels_cannot_duplicate_real_names(config_packages, alias_config_packages, caplog):
    # Arrange
    first = alias_config_packages["alias_host"] + ".apps.DefaultConfig"
    second = alias_config_packages["alias_changed"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps([], [PluginApp("first", first), PluginApp("second", second)])
    observed = _registry_metadata(merged)
    # Assert
    assert (
        merged == [first] and observed == [(config_packages["host"], "host_label")]
        and "duplicate app name" in caplog.text
    )


def test_a_real_alias_key_replacement_releases_its_old_label(config_packages, alias_config_packages):
    # Arrange
    existing = alias_config_packages["alias_host"]
    replacement = existing + ".apps.ReplacementConfig"
    newcomer = config_packages["collision"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps([existing], [PluginApp("replacement", replacement), PluginApp("new", newcomer)])
    observed = _registry_metadata(merged)
    # Assert
    assert merged == [replacement, newcomer] and observed == [
        (config_packages["host"], "replacement_label"),
        (config_packages["collision"], "host_label"),
    ]


def test_an_accepted_plugin_can_be_replaced_by_its_actual_alias_key(config_packages, alias_config_packages):
    # Arrange
    first = alias_config_packages["alias_host"] + ".apps.DefaultConfig"
    replacement = alias_config_packages["alias_host"] + ".apps.ReplacementConfig"
    # Act
    merged = with_plugin_apps([], [PluginApp("first", first), PluginApp("replacement", replacement)])
    observed = _registry_metadata(merged)
    # Assert
    assert merged == [replacement] and observed == [
        (config_packages["host"], "replacement_label")
    ]


def test_actual_key_replacement_releases_only_effective_name_and_label(config_packages, alias_config_packages):
    # Arrange
    existing = alias_config_packages["alias_host"]
    moved = existing + ".apps.MovedConfig"
    original_name = config_packages["host"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps([existing], [PluginApp("move", moved), PluginApp("original", original_name)])
    observed = _registry_metadata(merged)
    # Assert
    assert merged == [moved, original_name] and observed == [
        (config_packages["peer"], "moved_label"), (config_packages["host"], "host_label")
    ]


def test_key_replacement_cannot_take_another_real_name(config_packages, alias_config_packages):
    # Arrange
    alias, peer = alias_config_packages["alias_host"], config_packages["peer"]
    moved = alias + ".apps.MovedConfig"
    # Act
    merged = with_plugin_apps([alias, peer], [PluginApp("move", moved)])
    observed = _registry_metadata(merged)
    # Assert
    assert merged == [alias, peer] and observed == [
        (config_packages["host"], "host_label"), (peer, "peer_label")
    ]


def test_a_noncolliding_config_alias_remains_admitted(config_packages, alias_config_packages):
    # Arrange
    peer = config_packages["peer"]
    alias = alias_config_packages["alias_host"] + ".apps.DefaultConfig"
    # Act
    merged = with_plugin_apps([peer], [PluginApp("alias", alias)])
    observed = _registry_metadata(merged)
    # Assert
    assert merged == [peer, alias] and observed == [
        (peer, "peer_label"), (config_packages["host"], "host_label")
    ]
