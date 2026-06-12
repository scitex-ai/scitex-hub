"""Smoke tests for the live-paper cloud-side thin wrapper.

Mirrors ``tests/apps/agentic_journal_app/test_thin_wrapper.py`` — the
wrapper pattern is identical (apps.py + urls.py + manifest.json), only
the upstream package name changes.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "workspace"
    / "live_paper_app"
    / "manifest.json"
)


_UPSTREAM_AVAILABLE = importlib.util.find_spec("scitex_live_paper") is not None


def test_manifest_file_exists() -> None:
    # Arrange
    path = _MANIFEST_PATH
    # Act
    exists = path.is_file()
    # Assert
    assert exists is True


def test_manifest_app_name_matches_wrapper_package() -> None:
    # Arrange
    body = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    # Act
    app_name = body["app_name"]
    # Assert
    assert app_name == "live_paper_app"


def test_manifest_declares_scitex_live_paper_python_dep() -> None:
    # Arrange
    body = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    # Act
    python_deps = body["dependencies"]["python"]
    declares = any(dep.startswith("scitex-live-paper") for dep in python_deps)
    # Assert
    assert declares is True


def test_manifest_default_enabled_is_false_until_alpha_stabilises() -> None:
    # Arrange
    body = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    # Act
    default_enabled = body["default_enabled"]
    # Assert
    assert default_enabled is False


def test_wrapper_apps_module_imports() -> None:
    # Arrange
    expected_label = "live_paper_app"
    # Act
    from apps.workspace.live_paper_app import apps as wrapper_apps

    actual_label = wrapper_apps.LivePaperAppConfig.label
    # Assert
    assert actual_label == expected_label


@pytest.mark.skipif(
    not _UPSTREAM_AVAILABLE,
    reason=(
        "scitex-live-paper is not installed in this environment; "
        "wrapper urls.py eagerly include()s its URL conf and would "
        "ImportError. Skip — covered by upstream's own _django URL tests."
    ),
)
def test_wrapper_urls_module_imports() -> None:
    # Arrange
    min_patterns = 1
    # Act
    from apps.workspace.live_paper_app import urls as wrapper_urls

    actual = len(wrapper_urls.urlpatterns)
    # Assert
    assert actual >= min_patterns
