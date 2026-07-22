#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load-bearing containment tests for the filesystem permission validators.

After the path-containment sweep, ``validate_path_in_project`` went from
ZERO production callers to ~24 (it is now the single containment primitive
for the workspace/repository file endpoints). This file is its regression
guard: it pins the SIBLING-PREFIX case explicitly, so any future
"optimisation" of the validator back into a ``str.startswith`` is caught
immediately.

  validate_path_in_project(project_path, target)  — local component-wise
  validate_path_in_user_jail(user, target)        — tenant-ownership jail
  validate_remote_path_in_root(remote_root, full) — remote/SFTP POSIX syntax

The sibling-prefix case (``/p/demo`` must reject ``/p/demo-secret``) is the
one a prefix match gets wrong; a plain ``..`` case would pass under both.

No mocks (project rule); one assertion per test (STX-TQ007).
"""

from pathlib import Path

from apps.infra.project_app.services.filesystem.permissions import (
    validate_path_in_project,
    validate_remote_path_in_root,
)


class TestValidatePathInProject:
    """Component-wise containment for local project paths."""

    def test_nested_path_is_contained(self, tmp_path):
        # Arrange
        root = tmp_path / "proj"
        root.mkdir()
        target = root / "a" / "b.txt"
        # Act
        result = validate_path_in_project(root, target)
        # Assert
        assert result is True

    def test_root_itself_is_contained(self, tmp_path):
        # Arrange
        root = tmp_path / "proj"
        root.mkdir()
        # Act
        result = validate_path_in_project(root, root)
        # Assert
        assert result is True

    def test_sibling_prefix_directory_is_rejected(self, tmp_path):
        # Arrange — the case a startswith guard gets WRONG.
        root = tmp_path / "demo"
        sibling = tmp_path / "demo-secret"
        root.mkdir()
        sibling.mkdir()
        # Act
        result = validate_path_in_project(root, sibling / "SECRET.txt")
        # Assert
        assert result is False

    def test_dotdot_escape_is_rejected(self, tmp_path):
        # Arrange
        root = tmp_path / "proj"
        root.mkdir()
        # Act
        result = validate_path_in_project(root, root / ".." / "other" / "x")
        # Assert
        assert result is False


class TestValidateRemotePathInRoot:
    """Component-wise containment on remote POSIX path syntax (no resolve)."""

    def test_nested_remote_path_is_contained(self):
        # Arrange
        root = "/home/u/proj"
        full = "/home/u/proj/a/b.txt"
        # Act
        result = validate_remote_path_in_root(root, full)
        # Assert
        assert result is True

    def test_remote_root_itself_is_contained(self):
        # Arrange
        root = "/home/u/proj"
        # Act
        result = validate_remote_path_in_root(root, "/home/u/proj")
        # Assert
        assert result is True

    def test_remote_sibling_prefix_is_rejected(self):
        # Arrange — "/home/u/proj" must NOT admit "/home/u/proj-other".
        root = "/home/u/proj"
        full = "/home/u/proj-other/secret"
        # Act
        result = validate_remote_path_in_root(root, full)
        # Assert
        assert result is False

    def test_remote_dotdot_escape_is_rejected(self):
        # Arrange
        root = "/home/u/proj"
        full = "/home/u/proj/../proj-other/secret"
        # Act
        result = validate_remote_path_in_root(root, full)
        # Assert
        assert result is False


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
