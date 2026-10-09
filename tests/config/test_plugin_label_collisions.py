#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A ``scitex.apps`` plugin must not duplicate a local app's Django label.

REGRESSION (2026-10-09): ``scitex-clew`` 0.21.0 arrived transitively through
the ``scitex>=2.29.3`` umbrella (base Requires-Dist carries
``scitex-clew>=0.1.0`` unconditionally; CI installs ``.[all,dev]``) and
declares ``label = "clew_app"`` in
``scitex_clew/_django/apps.py`` — identical to hub's own
``apps/workspace/clew_app`` (``apps.py`` sets no label, so Django defaults
to ``clew_app``). ``installed_app_paths`` only replaces same-PACKAGE
entries, so both reached ``INSTALLED_APPS`` and ``django.setup()`` raised
``ImproperlyConfigured: Application labels aren't unique, duplicates:
clew_app`` — zero tests executed.

THE FIX (``config/settings/_optional_apps.py::_drop_label_collisions``):
the plugin whose label is already claimed outside its own package is
skipped with a warning; a plugin that REPLACES its same-package entry is
kept. The local app is never renamed: both sides ship migrations
(``apps/workspace/clew_app/migrations/0001_initial.py`` and the wheel's
``scitex_clew/_django/migrations/0001_initial.py``), so a label rename is
a data migration, not a one-liner.

WHY THE STUBS. ``_drop_label_collisions`` resolves labels by importing the
AppConfig class and duck-typing ``label``/``name`` (this module must stay
importable before Django is configured, so ``AppConfig`` itself is never
imported). Stub ``*.apps`` modules injected into ``sys.modules`` exercise
that path with no Django and no installed distributions; the final test
uses the REAL colliding pair and is skipped where they are absent.
"""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "config" / "settings" / "_optional_apps.py"


@pytest.fixture(name="optional_apps", scope="module")
def _optional_apps():
    """Load config/settings/_optional_apps.py with no package import."""
    spec = importlib.util.spec_from_file_location(
        "_optional_apps_under_test", MODULE_PATH
    )
    assert spec and spec.loader, f"could not load {MODULE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_apps_module(module_name: str, **configs) -> None:
    """Inject ``<module_name>.apps`` holding AppConfig-like classes."""
    parent, _, _ = module_name.rpartition(".")
    for name in (parent, module_name):
        if name not in sys.modules:
            mod = ModuleType(name)
            mod.__spec__ = ModuleSpec(name, loader=None)
            sys.modules[name] = mod
    apps_module = sys.modules[module_name]
    for cls_name, cls in configs.items():
        cls.__module__ = module_name
        setattr(apps_module, cls_name, cls)


def _make_config(name: str, label: str | None = None) -> type:
    attrs = {"name": name}
    if label is not None:
        attrs["label"] = label
    return type("StubConfig", (), attrs)


def _module_of(dotted: str) -> str:
    """Same-package rule mirroring ``scitex_app.plugins.app_module_of``."""
    parts = dotted.split(".")
    if len(parts) > 1 and parts[-1][:1].isupper():
        parts = parts[:-1]
    if len(parts) > 1 and parts[-1] == "apps":
        parts = parts[:-1]
    return ".".join(parts)


@pytest.fixture(name="stub_tree")
def _stub_tree():
    """A local app and two plugins colliding / coexisting with it."""
    _stub_apps_module(
        "stub_local_clew.apps",
        # Explicit label, mirroring the real local app whose dotted name
        # already defaults to `clew_app`.
        ClewAppConfig=_make_config("stub_local_clew", "clew_app"),
    )
    _stub_apps_module(
        "stub_up_clew.apps",
        ClewAppConfig=_make_config("stub_up_clew._django", "clew_app"),
    )
    _stub_apps_module(
        "stub_up_other.apps",
        OtherConfig=_make_config("stub_up_other._django", "other_app"),
    )
    yield
    for name in [
        "stub_local_clew",
        "stub_local_clew.apps",
        "stub_up_clew",
        "stub_up_clew.apps",
        "stub_up_other",
        "stub_up_other.apps",
    ]:
        sys.modules.pop(name, None)


def test_plugin_duplicating_a_local_app_label_is_skipped(
    optional_apps, stub_tree, caplog
) -> None:
    # Arrange — upstream plugin claims `clew_app`, owned by the local app.
    plugins = [
        SimpleNamespace(name="clew", app_config="stub_up_clew.apps.ClewAppConfig"),
        SimpleNamespace(name="other", app_config="stub_up_other.apps.OtherConfig"),
    ]

    # Act
    with caplog.at_level("WARNING"):
        kept = optional_apps._drop_label_collisions(
            ["stub_pkg"],
            plugins,
            extra_claims=["stub_local_clew"],
            app_module_of=_module_of,
        )

    # Assert — the colliding plugin is dropped, the other survives.
    assert [p.name for p in kept] == ["other"]
    assert any(
        "'clew'" in record.message and "clew_app" in record.message
        for record in caplog.records
    )


def test_plugin_replacing_its_same_package_entry_is_kept(
    optional_apps, stub_tree
) -> None:
    # Arrange — same package on both sides: a replace, not a collision.
    _stub_apps_module(
        "stub_fig.apps",
        FigConfig=_make_config("stub_fig._django", "fig_label"),
    )
    plugins = [
        SimpleNamespace(name="fig", app_config="stub_fig.apps.FigConfig"),
    ]
    try:
        # Act
        kept = optional_apps._drop_label_collisions(
            ["stub_fig.apps.FigConfig"],
            plugins,
            app_module_of=_module_of,
        )
    finally:
        sys.modules.pop("stub_fig", None)
        sys.modules.pop("stub_fig.apps", None)

    # Assert
    assert [p.name for p in kept] == ["fig"]


def test_plugin_with_unresolvable_label_is_kept(optional_apps, stub_tree) -> None:
    # Arrange — without proof of a collision the plugin keeps today's
    # behaviour (a broken wheel costs its own app, not hub startup).
    plugins = [
        SimpleNamespace(name="ghost", app_config="stub_missing.apps.GhostConfig"),
    ]

    # Act
    kept = optional_apps._drop_label_collisions(
        ["stub_pkg"], plugins, app_module_of=_module_of
    )

    # Assert
    assert [p.name for p in kept] == ["ghost"]


def test_real_clew_pair_skips_the_plugin(optional_apps) -> None:
    """The measured 2026-10-09 collision, with the real AppConfig classes."""
    pytest.importorskip("scitex_app.plugins", reason="no plugin API installed")
    pytest.importorskip("django", reason="local AppConfig needs Django")
    pytest.importorskip("scitex_clew._django.apps", reason="umbrella absent")

    from scitex_app.plugins import PluginApp  # type: ignore[import-not-found]

    if str(REPO) not in sys.path:  # pragma: no cover - harness dependent
        sys.path.insert(0, str(REPO))

    # Act
    merged = optional_apps.with_plugin_apps(
        ["scitex_ui"],
        [PluginApp("clew", "scitex_clew._django.apps.ClewAppConfig")],
        extra_claims=["apps.workspace.clew_app"],
    )

    # Assert — the plugin is dropped; the local app remains the only
    # `clew_app` claimant (`extra_claims` are label claims, not merged
    # entries — settings_shared.py merges LOCAL_APPS separately).
    assert "scitex_clew._django.apps.ClewAppConfig" not in merged
    assert (
        sum(
            1
            for entry in list(merged) + ["apps.workspace.clew_app"]
            if optional_apps._entry_claimed_labels(entry) == {"clew_app"}
        )
        == 1
    )
