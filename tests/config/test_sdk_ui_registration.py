"""SDK UI app registration: label-verified, never version-trusted."""

from __future__ import annotations

import sys
import types

from config.settings import _optional_apps as optional


def _install_fake_sdk_ui(label):
    """Inject a fake scitex_sdk.ui (+ .apps) pair; return saved modules."""
    saved = {
        name: sys.modules[name]
        for name in ("scitex_sdk.ui", "scitex_sdk.ui.apps")
        if name in sys.modules
    }
    ui = types.ModuleType("scitex_sdk.ui")
    apps = types.ModuleType("scitex_sdk.ui.apps")

    class ScitexUiConfig:
        name = "scitex_sdk.ui"

    # NOTE: assigned after creation — names in a class body do not close
    # over the enclosing function scope, so `label = label` would NameError.
    ScitexUiConfig.label = label
    apps.ScitexUiConfig = ScitexUiConfig
    ui.apps = apps
    sys.modules["scitex_sdk.ui"] = ui
    sys.modules["scitex_sdk.ui.apps"] = apps
    return saved


def _remove_fake_sdk_ui(saved):
    for name in ("scitex_sdk.ui.apps", "scitex_sdk.ui"):
        sys.modules.pop(name, None)
    sys.modules.update(saved)


def test_relabeled_sdk_ui_is_registered():
    saved = _install_fake_sdk_ui("scitex_sdk_ui")
    try:
        entries = optional.optional_upstream_apps()
    finally:
        _remove_fake_sdk_ui(saved)
    assert "scitex_sdk.ui.apps.ScitexUiConfig" in entries


def test_pre_relabel_sdk_ui_stays_excluded():
    saved = _install_fake_sdk_ui("scitex_ui")
    try:
        entries = optional.optional_upstream_apps()
    finally:
        _remove_fake_sdk_ui(saved)
    assert "scitex_sdk.ui.apps.ScitexUiConfig" not in entries
    assert not any("scitex_sdk.ui" in e for e in entries)


def test_absent_sdk_ui_registers_nothing(monkeypatch):
    # Popping sys.modules does NOT simulate absence: _installed() re-imports
    # from disk, so a real install would still resolve. Block resolution.
    monkeypatch.setattr(optional, "_installed", lambda module_path: None)
    entries = optional.optional_upstream_apps()
    assert not any("scitex_sdk.ui" in e for e in entries)
