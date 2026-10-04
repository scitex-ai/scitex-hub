"""Leaf companion declarations preserve the host's Django registration owners."""

from __future__ import annotations

import importlib
import sys

import pytest
from django.apps.registry import Apps
from scitex_sdk.app import plugins as sdk

from config.settings._app_config_metadata import (
    MetadataUnavailable,
    app_installation_entries,
)
from config.settings._optional_apps import _with_host_plugin_apps, with_plugin_apps


@pytest.fixture
def leaf_packages(tmp_path, monkeypatch):
    prefix = "companion_contract_" + tmp_path.name.replace("-", "_")
    root = tmp_path / prefix
    root.mkdir()
    (root / "__init__.py").write_text("")
    modules = {}
    for slug, label in (("editor", "editor"), ("chat", "chat"), ("owner", "owner"),
                        ("collision", "owner")):
        folder = root / slug
        folder.mkdir()
        (folder / "__init__.py").write_text("")
        name = prefix + "." + slug
        (folder / "apps.py").write_text(
            "from django.apps import AppConfig\n"
            "class Config(AppConfig):\n"
            "    default = True\n"
            f"    name = {name!r}\n"
            f"    label = {label!r}\n"
        )
        modules[slug] = name
    monkeypatch.syspath_prepend(str(tmp_path))
    yield modules, root
    for name in tuple(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            del sys.modules[name]


def declare(packages, entries, extra=""):
    modules, root = packages
    (root / "editor" / "__init__.py").write_text(
        f"INSTALLED_APPS_ENTRIES = {entries!r}\n" + extra
    )
    importlib.invalidate_caches()
    return sdk.PluginApp("editor", modules["editor"] + ".apps.Config")


def supported():
    return hasattr(sdk, "partition_companions")


def test_declarations_do_not_execute_a_leaf_package(leaf_packages):
    modules, _ = leaf_packages
    entries = (modules["editor"], modules["chat"] + ".apps.Config")
    declare(leaf_packages, entries, "unexpected_call_before_django_setup()\n")
    assert app_installation_entries(modules["editor"]) == entries
    assert modules["editor"] not in sys.modules


def test_old_plugins_do_not_execute_their_package_to_check_absence(leaf_packages):
    modules, root = leaf_packages
    (root / "editor" / "__init__.py").write_text("raise RuntimeError('early import')\n")
    assert app_installation_entries(modules["editor"]) == ()
    assert modules["editor"] not in sys.modules


def test_empty_declaration_keeps_primary_registration_on_existing_sdk(leaf_packages):
    plugin = declare(leaf_packages, ())
    assert with_plugin_apps([], [plugin]) == [plugin.app_config]


def test_companion_tuple_can_be_reexported_without_importing_it(leaf_packages):
    modules, root = leaf_packages
    entries = (modules["editor"], modules["chat"])
    (root / "editor" / "declarations.py").write_text(
        f"INSTALLED_APPS_ENTRIES = {entries!r}\n"
        "unexpected_declaration_import()\n"
    )
    (root / "editor" / "__init__.py").write_text(
        "from .declarations import INSTALLED_APPS_ENTRIES\n"
    )
    assert app_installation_entries(modules["editor"]) == entries
    assert modules["editor"] + ".declarations" not in sys.modules


def test_malformed_declaration_preserves_host_registration(leaf_packages):
    modules, _ = leaf_packages
    plugin = declare(leaf_packages, [modules["editor"], modules["chat"]])
    assert with_plugin_apps([modules["owner"]], [plugin]) == [modules["owner"]]


@pytest.mark.parametrize("body", [
    "INSTALLED_APPS_ENTRIES = ['leaf.apps.Config']\n",
    "INSTALLED_APPS_ENTRIES = ('leaf:Config',)\n",
    "INSTALLED_APPS_ENTRIES = ('',)\n",
    "INSTALLED_APPS_ENTRIES = (42,)\n",
    "INSTALLED_APPS_ENTRIES = tuple(['leaf.apps.Config'])\n",
    "INSTALLED_APPS_ENTRIES = ('leaf',)\nINSTALLED_APPS_ENTRIES += ('peer',)\n",
    "INSTALLED_APPS_ENTRIES = ('leaf',)\nglobals()['INSTALLED_APPS_ENTRIES'] = ()\n",
    "setattr(unknown_module, 'INSTALLED_APPS_ENTRIES', ('leaf',))\n",
    "if unknown_condition:\n    INSTALLED_APPS_ENTRIES = ('leaf',)\n",
])
def test_unprovable_companion_contract_is_refused(leaf_packages, body):
    modules, root = leaf_packages
    (root / "editor" / "__init__.py").write_text(body)
    with pytest.raises(MetadataUnavailable):
        app_installation_entries(modules["editor"])


def test_companion_and_primary_have_distinct_registered_identities(leaf_packages, caplog):
    modules, _ = leaf_packages
    editor, chat, owner = (modules[key] for key in ("editor", "chat", "owner"))
    plugin = declare(leaf_packages, (editor, chat + ".apps.Config"))
    result = with_plugin_apps([owner], [plugin])
    if not supported():
        assert result == [owner] and "does not support" in caplog.text
        return
    assert result == [owner, plugin.app_config, chat + ".apps.Config"]
    assert [(c.name, c.label) for c in Apps(installed_apps=result).get_app_configs()] == [
        (owner, "owner"), (editor, "editor"), (chat, "chat"),
    ]


def test_companion_label_cannot_replace_a_host_owner(leaf_packages):
    modules, _ = leaf_packages
    plugin = declare(leaf_packages, (modules["editor"], modules["collision"]))
    assert with_plugin_apps([modules["owner"]], [plugin]) == [modules["owner"]]


def test_unavailable_companion_preserves_existing_apps(leaf_packages):
    modules, _ = leaf_packages
    plugin = declare(leaf_packages, (modules["editor"], "absent_companion_xyz.apps.Config"))
    assert with_plugin_apps([modules["owner"]], [plugin]) == [modules["owner"]]


def test_reserved_companion_is_retained_by_the_host(leaf_packages):
    modules, _ = leaf_packages
    chat = modules["chat"]
    plugin = declare(leaf_packages, (modules["editor"], chat + ".apps.Config"))
    result = _with_host_plugin_apps([], [chat], [plugin])
    assert result == ([plugin.app_config] if supported() else [])
    if supported():
        assert [(c.name, c.label) for c in Apps(installed_apps=[*result, chat]).get_app_configs()] == [
            (modules["editor"], "editor"), (chat, "chat"),
        ]


def test_explicit_existing_companion_is_not_replaced_by_primary_inference(leaf_packages):
    modules, root = leaf_packages
    primary = modules["editor"] + ".apps.Config"
    companion = modules["editor"] + ".apps.ChatConfig"
    with (root / "editor" / "apps.py").open("a") as f:
        f.write(
            "class ChatConfig(Config):\n"
            "    default = False\n"
            f"    name = {modules['chat']!r}\n"
            "    label = 'chat'\n"
        )
    plugin = declare(leaf_packages, (modules["editor"], companion))
    result = with_plugin_apps([companion, modules["owner"]], [plugin])
    expected = [companion, modules["owner"], primary] if supported() else [companion, modules["owner"]]
    assert result == expected
    if supported():
        assert [(c.name, c.label) for c in Apps(installed_apps=result).get_app_configs()] == [
            (modules["chat"], "chat"), (modules["owner"], "owner"), (modules["editor"], "editor"),
        ]
