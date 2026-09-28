"""Containment regressions for the dev project file API."""

from pathlib import Path

import pytest

from apps.workspace.apps_app.views.dev_project_files import _resolve_safe_path


@pytest.mark.parametrize("fragment", ["/etc/passwd", "../secret", "sub/../../secret"])
def test_resolver_rejects_absolute_and_traversal(tmp_path, fragment):
    project = tmp_path / "project"
    project.mkdir()
    assert _resolve_safe_path(project, fragment) is None


def test_resolver_rejects_sibling_prefix_escape(tmp_path):
    project = tmp_path / "project"
    sibling = tmp_path / "project-secret"
    project.mkdir()
    sibling.mkdir()
    assert _resolve_safe_path(project, "../project-secret/key") is None


def test_resolver_rejects_symlink_escape(tmp_path):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / "escape").symlink_to(outside, target_is_directory=True)
    assert _resolve_safe_path(project, "escape/key") is None


def test_resolver_returns_resolved_child(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert (
        _resolve_safe_path(project, "src/main.py")
        == Path(project / "src/main.py").resolve()
    )
