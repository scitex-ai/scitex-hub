#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reality tests for the Writer workspace layout SSoT.

Runs against a REAL filesystem (``tmp_path``) — no mocks, per the
ecosystem no-mock rule: the thing under test is a path contract, and a
path contract is only meaningful against real directories.

Why this file exists: the same path was spelled in two places and
drifted twice, silently, in production.
  - 2026-07-08 every visitor slot was quarantined.
  - 2026-07-28 → 2026-08-02 every visitor saw an empty Writer editor.
Both times the undotted ``scitex/writer`` was checked while the real
``scitex_writer.ensure_workspace`` created dotted ``.scitex/writer``.
"""

from apps.infra.project_app.services.writer_workspace_layout import (
    MANUSCRIPT_DIRNAME,
    WRITER_WORKSPACE_RELPATH,
    get_manuscript_path,
    get_writer_workspace_path,
    is_writer_initialized,
)


class TestTheConstantItself:
    """The value is what the package creates. Pin it explicitly."""

    def test_workspace_relpath_is_dot_prefixed(self):
        # Arrange
        expected = ".scitex/writer"
        # Act
        actual = WRITER_WORKSPACE_RELPATH
        # Assert
        assert actual == expected, (
            "The workspace path must match what scitex_writer.ensure_workspace "
            "creates. An undotted value here quarantines visitor slots and "
            "blanks the Writer editor."
        )

    def test_manuscript_dirname_is_the_initialization_marker(self):
        # Arrange
        expected = "01_manuscript"
        # Act
        actual = MANUSCRIPT_DIRNAME
        # Assert
        assert actual == expected


class TestPathConstruction:
    def test_workspace_path_is_joined_under_the_project_root(self, tmp_path):
        # Arrange
        project_root = tmp_path / "some-project"
        # Act
        workspace = get_writer_workspace_path(project_root)
        # Assert
        assert workspace == project_root / ".scitex" / "writer"

    def test_workspace_path_is_not_the_undotted_legacy_spelling(self, tmp_path):
        # Arrange: the exact spelling that shipped broken, as a negative
        # control — without it, a passing positive test could still be
        # satisfied by a value that merely looks right.
        legacy = tmp_path / "scitex" / "writer"
        # Act
        workspace = get_writer_workspace_path(tmp_path)
        # Assert
        assert workspace != legacy

    def test_manuscript_path_sits_inside_the_workspace(self, tmp_path):
        # Arrange
        workspace = get_writer_workspace_path(tmp_path)
        # Act
        manuscript = get_manuscript_path(tmp_path)
        # Assert
        assert manuscript == workspace / MANUSCRIPT_DIRNAME

    def test_accepts_a_string_project_root(self, tmp_path):
        # Arrange
        as_string = str(tmp_path)
        # Act
        workspace = get_writer_workspace_path(as_string)
        # Assert
        assert workspace == get_writer_workspace_path(tmp_path)


class TestIsWriterInitialized:
    """Drives WRITER_CONFIG.writerInitialized, which decides whether the
    frontend mounts the editor at all — a false negative here renders a
    permanently empty page with no error."""

    def test_true_for_a_real_dotted_workspace(self, tmp_path):
        # Arrange
        (tmp_path / ".scitex" / "writer" / "01_manuscript").mkdir(parents=True)
        # Act
        initialized = is_writer_initialized(tmp_path)
        # Assert
        assert initialized is True

    def test_false_for_the_undotted_layout(self, tmp_path):
        # Arrange: build the WRONG layout. If this ever reports True the
        # undotted spelling has been re-admitted and every visitor gets
        # a blank editor again.
        (tmp_path / "scitex" / "writer" / "01_manuscript").mkdir(parents=True)
        # Act
        initialized = is_writer_initialized(tmp_path)
        # Assert
        assert initialized is False

    def test_false_when_workspace_exists_without_manuscript_dir(self, tmp_path):
        # Arrange
        (tmp_path / ".scitex" / "writer").mkdir(parents=True)
        # Act
        initialized = is_writer_initialized(tmp_path)
        # Assert
        assert initialized is False

    def test_false_for_an_empty_project_root(self, tmp_path):
        # Arrange
        empty_root = tmp_path / "untouched"
        empty_root.mkdir()
        # Act
        initialized = is_writer_initialized(empty_root)
        # Assert
        assert initialized is False


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
