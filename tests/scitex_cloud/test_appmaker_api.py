"""Tests for scitex_cloud.appmaker API, prefs, and registry manifest loading."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestRegistryManifestLoading:
    """Phase 1: Registry loads ModuleConfig from manifest.json files."""

    def test_loads_all_builtin_modules(self):
        from apps.infra.workspace_app.registry import get_all_modules

        modules = get_all_modules()
        assert len(modules) == 10

    def test_module_names(self):
        from apps.infra.workspace_app.registry import get_module_names

        names = get_module_names()
        expected = {
            "writer",
            "scholar",
            "vis",
            "clew",
            "home",
            "tools",
            "store",
            "docs",
            "figrecipe",
            "discovery",
        }
        assert names == expected

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
        )

        for rel_path in _BUILTIN_MANIFEST_PATHS:
            path = _APPS_ROOT / rel_path
            data = json.loads(path.read_text())
            assert (
                data.get("$schema") == "scitex-app-manifest"
            ), f"{rel_path} missing $schema"
            assert (
                data.get("$schema_version") == "1.0.0"
            ), f"{rel_path} missing $schema_version"


class TestInitAppRename:
    """Phase 2: scaffold() renamed to init_app()."""

    def test_init_app_importable(self):
        from scitex_cloud.appmaker import init_app

        assert callable(init_app)

    def test_scaffold_not_importable(self):
        with pytest.raises(ImportError):
            from scitex_cloud.appmaker import scaffold  # noqa: F401


class TestAppManagementAPI:
    """Phase 4: App management API with verb-form functions."""

    def test_get_current_reads_env(self):
        from scitex_cloud.appmaker import get_current

        os.environ["SCITEX_CURRENT_APP"] = "test-app"
        try:
            assert get_current() == "test-app"
        finally:
            del os.environ["SCITEX_CURRENT_APP"]

    def test_get_current_empty_when_unset(self):
        from scitex_cloud.appmaker import get_current

        os.environ.pop("SCITEX_CURRENT_APP", None)
        assert get_current() == ""

    def test_switch_to(self):
        from scitex_cloud.appmaker import get_current, switch_to

        switch_to("scholar")
        try:
            assert get_current() == "scholar"
        finally:
            os.environ.pop("SCITEX_CURRENT_APP", None)

    def test_list_all_from_registry(self):
        from scitex_cloud.appmaker import list_all

        apps = list_all()
        assert len(apps) == 10
        names = {a["name"] for a in apps}
        assert "writer" in names
        assert "scholar" in names

    def test_get_info_from_registry(self):
        from scitex_cloud.appmaker import get_info

        info = get_info("writer")
        assert info["name"] == "writer"
        assert info["label"] == "Writer"
        assert info["icon"] == "fas fa-pen"

    def test_get_info_unknown_app(self):
        from scitex_cloud.appmaker import get_info

        info = get_info("nonexistent_app")
        assert info == {}


class TestPreferences:
    """Phase 5: Per-user persistent preferences."""

    @pytest.fixture()
    def prefs_path(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td) / "prefs.json"

    def test_get_prefs_empty(self, prefs_path):
        from scitex_cloud.appmaker import get_prefs

        assert get_prefs("writer", prefs_path=prefs_path) == {}

    def test_set_and_get_prefs(self, prefs_path):
        from scitex_cloud.appmaker import get_prefs, set_prefs

        set_prefs("writer", {"theme": "dark", "font_size": 14}, prefs_path=prefs_path)
        result = get_prefs("writer", prefs_path=prefs_path)
        assert result == {"theme": "dark", "font_size": 14}

    def test_set_prefs_merges(self, prefs_path):
        from scitex_cloud.appmaker import get_prefs, set_prefs

        set_prefs("writer", {"theme": "dark"}, prefs_path=prefs_path)
        set_prefs("writer", {"font_size": 16}, prefs_path=prefs_path)
        result = get_prefs("writer", prefs_path=prefs_path)
        assert result == {"theme": "dark", "font_size": 16}

    def test_delete_prefs(self, prefs_path):
        from scitex_cloud.appmaker import delete_prefs, get_prefs, set_prefs

        set_prefs("writer", {"theme": "dark"}, prefs_path=prefs_path)
        assert delete_prefs("writer", prefs_path=prefs_path) is True
        assert get_prefs("writer", prefs_path=prefs_path) == {}

    def test_delete_prefs_nonexistent(self, prefs_path):
        from scitex_cloud.appmaker import delete_prefs

        assert delete_prefs("nonexistent", prefs_path=prefs_path) is False

    def test_list_prefs(self, prefs_path):
        from scitex_cloud.appmaker import list_prefs, set_prefs

        set_prefs("writer", {"theme": "dark"}, prefs_path=prefs_path)
        set_prefs("scholar", {"engine": "crossref"}, prefs_path=prefs_path)
        result = list_prefs(prefs_path=prefs_path)
        assert "writer" in result
        assert "scholar" in result


# EOF
