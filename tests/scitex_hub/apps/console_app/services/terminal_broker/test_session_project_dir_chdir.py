#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for BasePTY project_dir chdir resolution (no mocks; real fs).

Background: PR #246 fixed the host-side PTY chdir from hardcoded ``/tmp``
to ``HOME``. This module locks in the follow-up behaviour: when the
broker knows the workspace project root, the parent ``os.chdir`` lands
on that project dir (so bash PS1 \\w shows the project, not bare $HOME),
with a documented escalation to HOME and finally ``/tmp``.

All tests run real ``os.chdir`` against real ``tmp_path`` directories; a
``restore_cwd`` yield fixture snapshots and resets the working directory
around each test so a failure does not leak into siblings.
"""

import os
from pathlib import Path

import pytest

from apps.workspace.console_app.services.terminal_broker.session import BasePTY


@pytest.fixture
def restore_cwd():
    """Snapshot and restore CWD so a failing chdir does not leak."""
    # Arrange
    saved = os.getcwd()
    # Act
    yield
    # Assert
    try:
        os.chdir(saved)
    except OSError:
        os.chdir("/tmp")


class TestBasePTYProjectDirAttribute:
    """The new project_dir attribute is plumbed through __init__."""

    def test_basepty_default_project_dir_is_none(self):
        # Arrange
        pty_id = "test-pty-1"
        username = "alice"
        # Act
        pty = BasePTY(pty_id=pty_id, username=username)
        # Assert
        assert pty.project_dir is None

    def test_basepty_stores_project_dir_when_provided(self, tmp_path: Path):
        # Arrange
        project_dir = tmp_path / "proj" / "myproj"
        project_dir.mkdir(parents=True)
        # Act
        pty = BasePTY(
            pty_id="test-pty-2",
            username="alice",
            project_dir=project_dir,
        )
        # Assert
        assert pty.project_dir == project_dir


class TestBasePTYChdirToProjectDir:
    """_prepare_child_env chdirs into project_dir when it is set and exists."""

    def test_chdir_lands_on_project_dir_when_set_and_exists(
        self, tmp_path: Path, restore_cwd
    ):
        # Arrange
        project_dir = tmp_path / "alice" / "proj" / "myproj"
        project_dir.mkdir(parents=True)
        pty = BasePTY(
            pty_id="test-pty-3",
            username="alice",
            project_dir=project_dir,
        )
        # Act
        pty._prepare_child_env()
        # Assert
        assert Path(os.getcwd()).resolve() == project_dir.resolve()


class TestBasePTYChdirFallbackWhenProjectDirMissing:
    """When project_dir does not exist, escalation moves cwd off it."""

    def test_chdir_escalates_off_missing_project_dir(self, tmp_path: Path, restore_cwd):
        # Arrange
        missing_project_dir = tmp_path / "does" / "not" / "exist"
        username = "scitex-test-missing-proj-{}".format(os.getpid())
        pty = BasePTY(
            pty_id="test-pty-4",
            username=username,
            project_dir=missing_project_dir,
        )
        os.chdir(str(tmp_path))
        # Act
        pty._prepare_child_env()
        # Assert
        # The missing project_dir must NOT be where we ended up — the
        # escalation moved us off it (to HOME or /tmp).
        assert Path(os.getcwd()).resolve() != missing_project_dir.resolve()


class TestBasePTYChdirFallbackWhenProjectDirNone:
    """When project_dir is None, we leave the caller's starting cwd."""

    def test_chdir_does_not_stay_on_caller_cwd_when_project_dir_none(
        self, tmp_path: Path, restore_cwd
    ):
        # Arrange
        # Use a username unlikely to have /home/<u> on the runner so the
        # HOME chdir will fail and tip the resolver into /tmp; either
        # way we should NOT still be sitting on tmp_path.
        username = "scitex-test-no-home-{}".format(os.getpid())
        pty = BasePTY(
            pty_id="test-pty-5",
            username=username,
            project_dir=None,
        )
        os.chdir(str(tmp_path))
        # Act
        pty._prepare_child_env()
        # Assert
        assert Path(os.getcwd()).resolve() != tmp_path.resolve()


class TestBasePTYChdirFallbackToTmp:
    """When project_dir and HOME are both missing, /tmp is the floor."""

    def test_chdir_lands_on_tmp_when_project_dir_and_home_missing(
        self, tmp_path: Path, restore_cwd
    ):
        # Arrange
        missing_project_dir = tmp_path / "no" / "such" / "project"
        username = "scitex-test-fallback-{}".format(os.getpid())
        pty = BasePTY(
            pty_id="test-pty-6",
            username=username,
            project_dir=missing_project_dir,
        )
        os.chdir(str(tmp_path))
        # Act
        pty._prepare_child_env()
        # Assert
        assert Path(os.getcwd()).resolve() == Path("/tmp").resolve()


# EOF
