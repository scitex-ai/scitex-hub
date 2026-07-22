#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/public_app/templatetags/vite.py

Verifies that every vite_script entry used in templates resolves to
a TypeScript file that actually exists on disk.
"""

import os
import re
from pathlib import Path

import django
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
    try:
        django.setup()
    except RuntimeError:
        pass  # Already set up


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def collect_vite_script_entries() -> list[str]:
    """Scan all templates for {% vite_script 'entry' %} calls."""
    # Directories that contain user data or external clones — not project templates
    _EXCLUDE_DIRS = {"data", "node_modules", ".git", "__pycache__", "GITIGNORED"}

    entries = []
    pattern = re.compile(r"""{%\s*vite_script\s+['"]([^'"]+)['"]\s*%}""")
    templates_roots = [
        d
        for d in PROJECT_ROOT.rglob("templates")
        if not any(part in _EXCLUDE_DIRS for part in d.relative_to(PROJECT_ROOT).parts)
    ]
    for templates_root in templates_roots:
        for html in templates_root.rglob("*.html"):
            text = html.read_text(errors="replace")
            for match in pattern.finditer(text):
                entry = match.group(1)
                if entry not in entries:
                    entries.append(entry)
    return sorted(entries)


def resolve_path(entry_name: str) -> str:
    """Call the actual _entry_to_ts_path function."""
    setup_django()
    # Reset cache so each test run is fresh
    import apps.infra.public_app.templatetags.vite as vite_module

    vite_module._app_group_cache.clear()
    from apps.infra.public_app.templatetags.vite import _entry_to_ts_path

    return _entry_to_ts_path(entry_name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEntryToTsPath:
    """Unit tests for _entry_to_ts_path path resolution."""

    def test_writer_app_index(self):
        path = resolve_path("writer_app/index")
        full = PROJECT_ROOT / path
        assert full.exists(), f"writer_app/index → {path} — file not found"

    def test_console_app_workspace(self):
        path = resolve_path("console_app/workspace")
        full = PROJECT_ROOT / path
        assert full.exists(), f"console_app/workspace → {path} — file not found"

    def test_project_app_clone_button(self):
        path = resolve_path("project_app/clone_button")
        full = PROJECT_ROOT / path
        assert full.exists(), f"project_app/clone_button → {path} — file not found"

    def test_public_app_visitor_status(self):
        path = resolve_path("public_app/visitor-status")
        full = PROJECT_ROOT / path
        assert full.exists(), f"public_app/visitor-status → {path} — file not found"

    def test_shared_convention_path(self):
        path = resolve_path("shared/utils/console-interceptor")
        assert (
            path == "static/shared/ts/utils/console-interceptor.ts"
        ), f"Expected static/shared/ts/utils/console-interceptor.ts, got {path}"
        assert (PROJECT_ROOT / path).exists()

    def test_non_conventional_workspace_shell(self):
        path = resolve_path("workspace_app/workspace-shell")
        assert path == "static/workspace_app/ts/workspace-shell.ts"
        assert (PROJECT_ROOT / path).exists()

    def test_non_conventional_workspace_tree_init(self):
        path = resolve_path("shared/workspace-tree-init")
        assert path == "static/shared/ts/components/workspace-files-tree/auto-init.ts"
        assert (PROJECT_ROOT / path).exists()

    def test_non_conventional_resizer(self):
        path = resolve_path("shared/resizer")
        assert path == "static/shared/ts/components/resizer/index.ts"
        assert (PROJECT_ROOT / path).exists()

    def test_workspace_group_resolution(self):
        """Apps in apps/workspace/ are resolved with the workspace/ group."""
        setup_django()
        import apps.infra.public_app.templatetags.vite as vite_module

        vite_module._app_group_cache.clear()
        from apps.infra.public_app.templatetags.vite import _find_app_ts_path

        path = _find_app_ts_path("writer_app", "index")
        assert "workspace" in path, f"Expected workspace/ in path, got: {path}"
        assert (PROJECT_ROOT / path).exists()

    def test_infra_group_resolution(self):
        """Apps in apps/infra/ are resolved with the infra/ group."""
        setup_django()
        import apps.infra.public_app.templatetags.vite as vite_module

        vite_module._app_group_cache.clear()
        from apps.infra.public_app.templatetags.vite import _find_app_ts_path

        path = _find_app_ts_path("project_app", "clone_button")
        assert "infra" in path, f"Expected infra/ in path, got: {path}"
        assert (PROJECT_ROOT / path).exists()


class TestManifestMissFailLoud:
    """A manifest-lookup miss must fail LOUD, never silently return ''.

    DEBUG: TemplateSyntaxError (loud in dev).
    Production: a console.error <script> tag (visible to browser/QA console
    capture — a server-side log alone leaves the page silently blank).
    """

    @pytest.fixture()
    def vite_with_empty_manifest(self, tmp_path):
        """Point BASE_DIR at a REAL empty manifest.json on disk.

        No fake internals: get_manifest() reads the actual file; the
        module-level cache is reset around the test so state cannot leak
        between this fixture's tmp manifest and the repo's real one.
        """
        setup_django()
        from django.test import override_settings

        import apps.infra.public_app.templatetags.vite as vite_module

        manifest_dir = tmp_path / "staticfiles" / "vite" / ".vite"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "manifest.json").write_text("{}")

        def _reset_manifest_cache():
            vite_module._manifest_cache = None
            vite_module._manifest_mtime = 0.0
            vite_module._manifest_name_index = None

        override = override_settings(BASE_DIR=tmp_path)
        override.enable()
        _reset_manifest_cache()
        try:
            yield vite_module
        finally:
            override.disable()
            _reset_manifest_cache()

    def test_vite_script_manifest_miss_in_debug_raises_template_syntax_error(
        self, vite_with_empty_manifest
    ):
        # Arrange
        from django.template import TemplateSyntaxError
        from django.test import override_settings

        # Act
        # (the vite_script call itself is the act under assertion below)
        # Assert
        with override_settings(DEBUG=True, VITE_USE_BUILD=True):
            with pytest.raises(TemplateSyntaxError, match="workspace-shell"):
                vite_with_empty_manifest.vite_script("workspace_app/workspace-shell")

    def test_vite_script_manifest_miss_in_production_emits_console_error_tag(
        self, vite_with_empty_manifest
    ):
        # Arrange
        from django.test import override_settings

        # Act
        with override_settings(DEBUG=False):
            html = vite_with_empty_manifest.vite_script("workspace_app/workspace-shell")
        # Assert
        assert "console.error" in html and "workspace_app/workspace-shell" in html

    def test_vite_preload_manifest_miss_in_debug_raises_template_syntax_error(
        self, vite_with_empty_manifest
    ):
        # Arrange
        from django.template import TemplateSyntaxError
        from django.test import override_settings

        # Act
        # (the vite_preload call itself is the act under assertion below)
        # Assert
        with override_settings(DEBUG=True, VITE_USE_BUILD=True):
            with pytest.raises(TemplateSyntaxError, match="workspace-shell"):
                vite_with_empty_manifest.vite_preload("workspace_app/workspace-shell")

    def test_vite_preload_manifest_miss_in_production_emits_console_error_tag(
        self, vite_with_empty_manifest
    ):
        # Arrange
        from django.test import override_settings

        # Act
        with override_settings(DEBUG=False):
            html = vite_with_empty_manifest.vite_preload(
                "workspace_app/workspace-shell"
            )
        # Assert
        assert "console.error" in html and "workspace_app/workspace-shell" in html


class TestAllTemplateEntries:
    """Parametrized test: every vite_script entry in templates must resolve to an existing file."""

    @pytest.fixture(scope="class")
    def entries(self):
        return collect_vite_script_entries()

    def test_entries_discovered(self, entries):
        assert len(entries) > 0, "No vite_script entries found in templates"

    @pytest.mark.parametrize(
        "entry",
        collect_vite_script_entries(),
    )
    def test_entry_resolves_to_existing_file(self, entry):
        path = resolve_path(entry)
        full = PROJECT_ROOT / path
        assert full.exists(), (
            f"vite_script '{entry}' → '{path}' — file not found on disk\n"
            f"  Full path checked: {full}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
