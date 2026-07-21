"""Tests for scitex_hub.appmaker._deps — dependency checking, installation, and container building."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestCheckDeps:
    """check_deps() identifies missing dependencies from a manifest."""

    def test_empty_deps_returns_empty(self):
        from scitex_hub.appmaker import check_deps

        manifest = {"dependencies": {"python": [], "system": [], "node": [], "r": []}}
        assert check_deps(manifest) == {}

    def test_no_deps_key_returns_empty(self):
        from scitex_hub.appmaker import check_deps

        assert check_deps({}) == {}
        assert check_deps({"dependencies": None}) == {}

    def test_detects_missing_python_package(self):
        from scitex_hub.appmaker import check_deps

        manifest = {"dependencies": {"python": ["nonexistent_pkg_xyz_12345"]}}
        missing = check_deps(manifest)
        assert "python" in missing
        assert "nonexistent_pkg_xyz_12345" in missing["python"]

    def test_installed_python_package_not_missing(self):
        from scitex_hub.appmaker import check_deps

        # pytest itself must be installed
        manifest = {"dependencies": {"python": ["pytest"]}}
        missing = check_deps(manifest)
        assert "python" not in missing

    def test_version_spec_parsed_correctly(self):
        from scitex_hub.appmaker import check_deps

        # pytest is installed, so even with version spec it should pass
        manifest = {"dependencies": {"python": ["pytest>=1.0"]}}
        missing = check_deps(manifest)
        assert "python" not in missing

    def test_unknown_dep_type_skipped(self):
        from scitex_hub.appmaker import check_deps

        manifest = {"dependencies": {"julia": ["SomePackage"]}}
        assert check_deps(manifest) == {}


class TestCheckDepsFromManifest:
    """check_deps_from_manifest() loads manifest file first."""

    def test_loads_and_checks(self):
        from scitex_hub.appmaker import check_deps_from_manifest

        with tempfile.TemporaryDirectory() as td:
            manifest_path = Path(td) / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "$schema": "scitex-app-manifest",
                        "$schema_version": "1.0.0",
                        "dependencies": {"python": ["pytest"]},
                    }
                )
            )
            missing = check_deps_from_manifest(manifest_path)
            assert "python" not in missing


class TestInstallDeps:
    """install_deps() dispatches to the correct installer."""

    def test_empty_specs_succeeds(self):
        from scitex_hub.appmaker import install_deps

        manifest = {"dependencies": {"python": []}}
        result = install_deps(manifest, "python")
        assert result["success"] is True
        assert result["installed"] == []

    def test_unknown_type_fails(self):
        from scitex_hub.appmaker import install_deps

        manifest = {"dependencies": {"julia": ["Flux"]}}
        result = install_deps(manifest, "julia")
        assert result["success"] is False
        assert "No installer" in result["error"]

    def test_missing_dep_type_succeeds(self):
        from scitex_hub.appmaker import install_deps

        manifest = {"dependencies": {"python": ["pytest"]}}
        result = install_deps(manifest, "node")
        assert result["success"] is True

    @patch("subprocess.run")
    def test_python_install_calls_pip(self, mock_run):
        from scitex_hub.appmaker import install_deps

        mock_run.return_value.returncode = 0
        manifest = {"dependencies": {"python": ["numpy>=1.24"]}}
        result = install_deps(manifest, "python")
        assert result["success"] is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "pip" in call_args
        assert "numpy>=1.24" in call_args


class TestFormatMissingReport:
    """format_missing_report() produces readable output."""

    def test_no_missing(self):
        from scitex_hub.appmaker import format_missing_report

        assert "satisfied" in format_missing_report({}).lower()

    def test_with_missing(self):
        from scitex_hub.appmaker import format_missing_report

        report = format_missing_report(
            {"python": ["numpy", "scipy"], "system": ["texlive-full"]}
        )
        assert "Python (pip)" in report
        assert "numpy" in report
        assert "System (apt)" in report
        assert "texlive-full" in report


class TestParsePkgName:
    """_parse_pkg_name extracts name from version specs."""

    def test_simple_name(self):
        from scitex_hub.appmaker._deps import _parse_pkg_name

        assert _parse_pkg_name("numpy") == "numpy"

    def test_gte_spec(self):
        from scitex_hub.appmaker._deps import _parse_pkg_name

        assert _parse_pkg_name("numpy>=1.24") == "numpy"

    def test_eq_spec(self):
        from scitex_hub.appmaker._deps import _parse_pkg_name

        assert _parse_pkg_name("react==18.0.0") == "react"

    def test_tilde_spec(self):
        from scitex_hub.appmaker._deps import _parse_pkg_name

        assert _parse_pkg_name("flask~=2.0") == "flask"


class TestBuildContainer:
    """build_container() builds .sif from .def or validates existing .sif."""

    def test_no_manifest(self):
        from scitex_hub.appmaker import build_container

        with tempfile.TemporaryDirectory() as td:
            result = build_container(Path(td))
            assert result["success"] is False
            assert "No manifest.json" in result["error"]

    def test_no_container_field(self):
        from scitex_hub.appmaker import build_container

        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.json"
            manifest.write_text(json.dumps({"container": None}))
            result = build_container(Path(td))
            assert result["success"] is False
            assert "No container field" in result["error"]

    def test_sif_exists(self):
        from scitex_hub.appmaker import build_container

        with tempfile.TemporaryDirectory() as td:
            sif = Path(td) / "app.sif"
            sif.write_text("fake sif")
            manifest = Path(td) / "manifest.json"
            manifest.write_text(json.dumps({"container": "app.sif"}))
            result = build_container(Path(td))
            assert result["success"] is True
            assert result["sif_path"] == str(sif)

    def test_sif_not_found(self):
        from scitex_hub.appmaker import build_container

        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.json"
            manifest.write_text(json.dumps({"container": "missing.sif"}))
            result = build_container(Path(td))
            assert result["success"] is False
            assert "not found" in result["error"].lower()

    def test_invalid_extension(self):
        from scitex_hub.appmaker import build_container

        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.json"
            manifest.write_text(json.dumps({"container": "Dockerfile"}))
            result = build_container(Path(td))
            assert result["success"] is False
            assert ".def or .sif" in result["error"]

    def test_def_file_not_found(self):
        from scitex_hub.appmaker import build_container

        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.json"
            manifest.write_text(json.dumps({"container": "app.def"}))
            result = build_container(Path(td))
            assert result["success"] is False
            assert "Def file not found" in result["error"]


class TestBuiltinManifestDeps:
    """All builtin manifest.json files have valid dependencies structure."""

    def test_all_manifests_have_deps(self):
        from apps.infra.workspace_app.registry import (
            _APPS_ROOT,
            _BUILTIN_MANIFEST_PATHS,
        )

        for rel_path in _BUILTIN_MANIFEST_PATHS:
            path = _APPS_ROOT / rel_path
            data = json.loads(path.read_text())
            deps = data.get("dependencies")
            assert deps is not None, f"{rel_path} missing dependencies"
            assert isinstance(deps, dict), f"{rel_path} dependencies not a dict"
            for key in ("python", "system", "node", "r"):
                assert key in deps, f"{rel_path} missing dependencies.{key}"
                assert isinstance(
                    deps[key], list
                ), f"{rel_path} dependencies.{key} not a list"


# EOF
