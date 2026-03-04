#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/services/terminal_broker/session.py

Tests BasePTY lifecycle (spawn, write, resize, close, scrollback)
and TerminalSession command building.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.console_app.services.terminal_broker.session import (
    BasePTY,
    SessionState,
    TerminalSession,
)

# ---------------------------------------------------------------------------
# BasePTY state and lifecycle
# ---------------------------------------------------------------------------


class TestBasePTYInitialState:
    """BasePTY starts in DEAD state with no fd or pid."""

    def test_initial_state_is_dead(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty.state == SessionState.DEAD

    def test_initial_pid_is_none(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty.pid is None

    def test_initial_fd_is_none(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty.fd is None

    def test_running_property_false_when_dead(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty.running is False

    def test_default_screen_session(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty.screen_session == "scitex-0"

    def test_custom_screen_session(self):
        pty = BasePTY(pty_id="test-id", username="alice", screen_session="custom-1")
        assert pty.screen_session == "custom-1"


class TestBasePTYSpawn:
    """BasePTY.spawn forks a PTY and transitions to RUNNING."""

    @patch("apps.console_app.services.terminal_broker.session.pty.fork")
    def test_spawn_sets_running(self, mock_fork):
        mock_fork.return_value = (1234, 5)  # parent: pid=1234, fd=5
        pty = BasePTY(pty_id="test-id", username="alice")
        # Provide _exec_in_child so it doesn't raise
        pty._exec_in_child = MagicMock()
        result = pty.spawn()
        assert result is True
        assert pty.state == SessionState.RUNNING
        assert pty.pid == 1234
        assert pty.fd == 5

    @patch("apps.console_app.services.terminal_broker.session.pty.fork")
    def test_spawn_increments_count(self, mock_fork):
        mock_fork.return_value = (1234, 5)
        pty = BasePTY(pty_id="test-id", username="alice")
        pty._exec_in_child = MagicMock()
        assert pty.spawn_count == 0
        pty.spawn()
        assert pty.spawn_count == 1

    @patch("apps.console_app.services.terminal_broker.session.pty.fork")
    def test_spawn_failure_sets_dead(self, mock_fork):
        mock_fork.side_effect = OSError("fork failed")
        pty = BasePTY(pty_id="test-id", username="alice")
        pty._exec_in_child = MagicMock()
        result = pty.spawn()
        assert result is False
        assert pty.state == SessionState.DEAD

    @patch("apps.console_app.services.terminal_broker.session.pty.fork")
    def test_running_property_true_when_spawned(self, mock_fork):
        mock_fork.return_value = (1234, 5)
        pty = BasePTY(pty_id="test-id", username="alice")
        pty._exec_in_child = MagicMock()
        pty.spawn()
        assert pty.running is True


class TestBasePTYWrite:
    """BasePTY.write sends data to the PTY fd."""

    @patch("apps.console_app.services.terminal_broker.session.os.write")
    def test_write_calls_os_write(self, mock_write):
        pty = BasePTY(pty_id="test-id", username="alice")
        pty.fd = 5
        pty.write(b"hello")
        mock_write.assert_called_once_with(5, b"hello")

    @patch("apps.console_app.services.terminal_broker.session.os.write")
    def test_write_noop_when_no_fd(self, mock_write):
        pty = BasePTY(pty_id="test-id", username="alice")
        pty.fd = None
        pty.write(b"hello")
        mock_write.assert_not_called()


class TestBasePTYResize:
    """BasePTY.resize changes the PTY window size."""

    @patch("apps.console_app.services.terminal_broker.session.termios.tcsetwinsize")
    def test_resize_calls_tcsetwinsize(self, mock_resize):
        pty = BasePTY(pty_id="test-id", username="alice")
        pty.fd = 5
        pty.resize(24, 80)
        mock_resize.assert_called_once_with(5, (24, 80))

    @patch("apps.console_app.services.terminal_broker.session.termios.tcsetwinsize")
    def test_resize_noop_when_no_fd(self, mock_resize):
        pty = BasePTY(pty_id="test-id", username="alice")
        pty.fd = None
        pty.resize(24, 80)
        mock_resize.assert_not_called()


class TestBasePTYClose:
    """BasePTY.close cleans up fd and transitions to DEAD."""

    @patch("apps.console_app.services.terminal_broker.session.os.close")
    @patch("apps.console_app.services.terminal_broker.session.os.waitpid")
    @patch("apps.console_app.services.terminal_broker.session.os.kill")
    def test_close_sets_dead(self, mock_kill, mock_waitpid, mock_close):
        pty = BasePTY(pty_id="test-id", username="alice")
        pty.pid = 1234
        pty.fd = 5
        pty.state = SessionState.RUNNING
        pty.close()
        assert pty.state == SessionState.DEAD
        assert pty.pid is None
        assert pty.fd is None

    @patch("apps.console_app.services.terminal_broker.session.os.close")
    @patch("apps.console_app.services.terminal_broker.session.os.waitpid")
    @patch("apps.console_app.services.terminal_broker.session.os.kill")
    def test_close_sends_sigterm(self, mock_kill, mock_waitpid, mock_close):
        import signal

        pty = BasePTY(pty_id="test-id", username="alice")
        pty.pid = 1234
        pty.fd = 5
        pty.close()
        mock_kill.assert_called_once_with(1234, signal.SIGTERM)


class TestBasePTYScrollback:
    """BasePTY scrollback buffer stores recent output."""

    def test_empty_scrollback(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty.get_scrollback() == b""

    def test_scrollback_stores_data(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        pty._scrollback.append(b"hello ")
        pty._scrollback.append(b"world")
        assert pty.get_scrollback() == b"hello world"

    def test_scrollback_has_max_length(self):
        pty = BasePTY(pty_id="test-id", username="alice")
        assert pty._scrollback.maxlen == 256


class TestBasePTYRespawn:
    """BasePTY.respawn cleans up old PTY and spawns new one."""

    @patch("apps.console_app.services.terminal_broker.session.pty.fork")
    @patch("apps.console_app.services.terminal_broker.session.os.close")
    @patch("apps.console_app.services.terminal_broker.session.os.waitpid")
    @patch("apps.console_app.services.terminal_broker.session.os.kill")
    def test_respawn_cleans_up_and_spawns(
        self, mock_kill, mock_waitpid, mock_close, mock_fork
    ):
        mock_fork.return_value = (5678, 9)
        pty = BasePTY(pty_id="test-id", username="alice")
        pty._exec_in_child = MagicMock()
        pty.pid = 1234
        pty.fd = 5
        result = pty.respawn()
        assert result is True
        assert pty.pid == 5678
        assert pty.fd == 9


class TestBasePTYPrepareChildEnv:
    """BasePTY._prepare_child_env sets HOME, USER, TERM etc."""

    @patch("apps.console_app.services.terminal_broker.session.os.chdir")
    def test_env_contains_username(self, mock_chdir):
        pty = BasePTY(pty_id="test-id", username="alice")
        env = pty._prepare_child_env()
        assert env["HOME"] == "/home/alice"
        assert env["USER"] == "alice"
        assert env["LOGNAME"] == "alice"
        assert env["TERM"] == "xterm-256color"
        assert env["SHELL"] == "/bin/bash"


# ---------------------------------------------------------------------------
# TerminalSession
# ---------------------------------------------------------------------------


class TestTerminalSessionInit:
    """TerminalSession stores project info for srun command building."""

    def test_stores_project_info(self):
        session = TerminalSession(
            session_id="sess-1",
            username="alice",
            user_data_dir=Path("/data/alice"),
            project_dir=Path("/data/alice/proj/myproj"),
            container_path="/opt/scitex/container.sif",
            project_slug="myproj",
        )
        assert session.username == "alice"
        assert session.project_slug == "myproj"
        assert session.container_path == "/opt/scitex/container.sif"
        assert session.session_id == "sess-1"


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
