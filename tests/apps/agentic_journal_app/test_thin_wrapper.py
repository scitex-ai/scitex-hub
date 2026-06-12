"""Smoke tests for the agentic-journal cloud-side thin wrapper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "workspace"
    / "agentic_journal_app"
    / "manifest.json"
)


_UPSTREAM_AVAILABLE = importlib.util.find_spec("scitex_agentic_journal") is not None


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
    assert app_name == "agentic_journal_app"


def test_manifest_declares_scitex_agentic_journal_python_dep() -> None:
    # Arrange
    body = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    # Act
    python_deps = body["dependencies"]["python"]
    declares = any(dep.startswith("scitex-agentic-journal") for dep in python_deps)
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
    # importing alone is the act we are checking
    # Act
    from apps.workspace.agentic_journal_app import apps as wrapper_apps

    # Assert
    assert wrapper_apps.AgenticJournalAppConfig.label == "agentic_journal_app"


@pytest.mark.skipif(
    not _UPSTREAM_AVAILABLE,
    reason=(
        "scitex-agentic-journal is not installed in this environment; "
        "wrapper urls.py eagerly include()s its URL conf and would "
        "ImportError. Skip — covered by upstream's own _django URL tests."
    ),
)
def test_wrapper_urls_module_imports() -> None:
    # Arrange
    # Act
    from apps.workspace.agentic_journal_app import urls as wrapper_urls

    # Assert
    assert len(wrapper_urls.urlpatterns) >= 1
