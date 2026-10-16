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
        label = label

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


def test_absent_sdk_ui_registers_nothing():
    saved = {
        name: sys.modules.pop(name)
        for name in ("scitex_sdk.ui", "scitex_sdk.ui.apps")
        if name in sys.modules
    }
    try:
        entries = optional.optional_upstream_apps()
    finally:
        sys.modules.update(saved)
    assert not any("scitex_sdk.ui" in e for e in entries)
