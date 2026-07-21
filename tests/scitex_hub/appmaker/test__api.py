"""Tests for scitex_hub.appmaker API, prefs, and registry manifest loading."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestRegistryManifestLoading:
    """Phase 1: Registry loads ModuleConfig from manifest.json files."""

    def test_loads_all_builtin_modules(self):
        # get_all_modules() returns one ModuleConfig per builtin manifest path,
        # so the count is derived from the registry's manifest list rather than
        # a hardcoded number that drifts whenever an app is added/removed.
        from apps.infra.workspace_app.registry import (
            _BUILTIN_MANIFEST_PATHS,
            get_all_modules,
        )

        modules = get_all_modules()
        assert len(modules) == len(_BUILTIN_MANIFEST_PATHS)

    def test_module_names(self):
        from apps.infra.workspace_app.registry import get_module_names

        names = get_module_names()
        # Core modules that must always be registered. (Asserting a subset
        # keeps the test stable as optional apps are added/removed; the old
        # exact-set expectation predated the figrecipe rename and the
        # console/comms app additions and had gone stale.)
        expected_core = {
            "writer",
            "scholar",
            "clew",
            "home",
            "tools",
            "store",
            "docs",
            "figrecipe",
            "discovery",
            "comms",
            "console",
        }
        assert (
            expected_core <= names
        ), f"missing core modules: {sorted(expected_core - names)}"

    def test_clew_has_svg_icons(self):
        from apps.infra.workspace_app.registry import get_module

        clew = get_module("clew")
        assert clew is not None
        assert clew.icon_svg_tab
        assert clew.icon_svg_nav
        assert clew.default_enabled is False

    def test_writer_has_extensions(self):
        from apps.infra.workspace_app.registry import get_module

        writer = get_module("writer")
        assert writer is not None
        assert ".tex" in writer.allowed_extensions
        assert writer.context_builder != ""

    def test_manifest_files_have_schema(self):
        """All manifest.json files must have $schema and $schema_version."""
        from apps.infra.workspace_app.registry import (
            _APPS_ROOT,
            _BUILTIN_MANIFEST_PATHS,
            _SUPPORTED_SCHEMA_VERSIONS,
        )

        for rel_path in _BUILTIN_MANIFEST_PATHS:
            path = _APPS_ROOT / rel_path
            data = json.loads(path.read_text())
            assert (
                data.get("$schema") == "scitex-app-manifest"
            ), f"{rel_path} missing $schema"
            assert data.get("$schema_version") in _SUPPORTED_SCHEMA_VERSIONS, (
                f"{rel_path} has unsupported $schema_version "
                f"{data.get('$schema_version')!r} "
                f"(supported: {sorted(_SUPPORTED_SCHEMA_VERSIONS)})"
            )


class TestInitAppRename:
    """Phase 2: scaffold() renamed to init_app()."""

    def test_init_app_importable(self):
        from scitex_hub.appmaker import init_app

        assert callable(init_app)

    def test_scaffold_not_importable(self):
        with pytest.raises(ImportError):
            from scitex_hub.appmaker import scaffold  # noqa: F401


class TestAppManagementAPI:
    """Phase 4: App management API with verb-form functions."""

    def test_get_current_reads_env(self):
        from scitex_hub.appmaker import get_current

        os.environ["SCITEX_CURRENT_APP"] = "test-app"
        try:
            assert get_current() == "test-app"
        finally:
            del os.environ["SCITEX_CURRENT_APP"]

    def test_get_current_empty_when_unset(self):
        from scitex_hub.appmaker import get_current

        os.environ.pop("SCITEX_CURRENT_APP", None)
        assert get_current() == ""

    def test_switch_to(self):
        from scitex_hub.appmaker import get_current, switch_to

        switch_to("scholar")
        try:
            assert get_current() == "scholar"
        finally:
            os.environ.pop("SCITEX_CURRENT_APP", None)

    def test_list_all_from_registry(self):
        from apps.infra.workspace_app.registry import _BUILTIN_MANIFEST_PATHS
        from scitex_hub.appmaker import list_all

        apps = list_all()
        # One entry per builtin manifest (derived, not a hardcoded count that
        # drifts as apps are added/removed).
        assert len(apps) == len(_BUILTIN_MANIFEST_PATHS)
        names = {a["name"] for a in apps}
        assert {"writer", "scholar"} <= names

    def test_get_info_from_registry(self):
        from scitex_hub.appmaker import get_info

        info = get_info("writer")
        assert info["name"] == "writer"
        assert info["label"] == "Writer"
        assert info["icon"] == "fas fa-pen"

    def test_get_info_unknown_app(self):
        from scitex_hub.appmaker import get_info

        info = get_info("nonexistent_app")
        assert info == {}


class TestPreferences:
    """Phase 5: Per-user persistent preferences."""

    @pytest.fixture()
    def prefs_path(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td) / "prefs.json"

    def test_get_prefs_empty(self, prefs_path):
        from scitex_hub.appmaker import get_prefs

        assert get_prefs("writer", prefs_path=prefs_path) == {}

    def test_set_and_get_prefs(self, prefs_path):
        from scitex_hub.appmaker import get_prefs, set_prefs

        set_prefs("writer", {"theme": "dark", "font_size": 14}, prefs_path=prefs_path)
        result = get_prefs("writer", prefs_path=prefs_path)
        assert result == {"theme": "dark", "font_size": 14}

    def test_set_prefs_merges(self, prefs_path):
        from scitex_hub.appmaker import get_prefs, set_prefs

        set_prefs("writer", {"theme": "dark"}, prefs_path=prefs_path)
        set_prefs("writer", {"font_size": 16}, prefs_path=prefs_path)
        result = get_prefs("writer", prefs_path=prefs_path)
        assert result == {"theme": "dark", "font_size": 16}

    def test_delete_prefs(self, prefs_path):
        from scitex_hub.appmaker import delete_prefs, get_prefs, set_prefs

        set_prefs("writer", {"theme": "dark"}, prefs_path=prefs_path)
        assert delete_prefs("writer", prefs_path=prefs_path) is True
        assert get_prefs("writer", prefs_path=prefs_path) == {}

    def test_delete_prefs_nonexistent(self, prefs_path):
        from scitex_hub.appmaker import delete_prefs

        assert delete_prefs("nonexistent", prefs_path=prefs_path) is False

    def test_list_prefs(self, prefs_path):
        from scitex_hub.appmaker import list_prefs, set_prefs

        set_prefs("writer", {"theme": "dark"}, prefs_path=prefs_path)
        set_prefs("scholar", {"engine": "crossref"}, prefs_path=prefs_path)
        result = list_prefs(prefs_path=prefs_path)
        assert "writer" in result
        assert "scholar" in result


# EOF
