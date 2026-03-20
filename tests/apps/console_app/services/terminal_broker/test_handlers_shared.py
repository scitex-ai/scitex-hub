#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/services/terminal_broker/_handlers_shared.py

Tests per-user allocation key, shell reattachment, stop_allocation cleanup,
and cooldown logic.
"""

import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from apps.workspace.console_app.services.terminal_broker._handlers_shared import (
    handle_spawn_shared,
    handle_stop_allocation,
    stop_all_allocations,
)
from apps.workspace.console_app.services.terminal_broker.allocation import (
    AllocationState,
)
from apps.workspace.console_app.services.terminal_broker.session import SessionState
from apps.workspace.console_app.services.terminal_broker.shell import Shell


def _make_broker():
    """Create a minimal broker mock with required attributes."""
    broker = MagicMock()
    broker.sessions = {}
    broker.session_index = {}
    broker.allocations = {}
    broker.alloc_index = {}
    broker.shells = {}
    broker.shell_index = {}
    broker.lock = threading.Lock()
    return broker


# ---------------------------------------------------------------------------
# Allocation key is per-user
# ---------------------------------------------------------------------------


class TestAllocationKeyPerUser:
    """Shared allocation uses alloc_key = (username,) — one per user."""

    @patch(
        "apps.workspace.console_app.services.terminal_broker._handlers_shared.Allocation"
    )
    @patch("apps.workspace.console_app.services.terminal_broker._handlers_shared.Shell")
    @patch(
        "apps.workspace.console_app.services.terminal_broker._handlers_shared.SLURM_TIME_LIMIT_SECONDS",
        14400,
    )
    @patch(
        "apps.workspace.console_app.views.terminal.config.SHOW_MOTD",
        False,
    )
    @patch(
        "apps.workspace.console_app.services.terminal_broker._handlers_shared._hard_fail_info",
        {},
    )
    @patch(
        "apps.workspace.console_app.services.terminal_broker._handlers_shared._wait_for_node_or_fail",
        return_value=(True, ""),
    )
    def test_same_user_different_projects_share_allocation(
        self, mock_node_check, MockShell, MockAllocation
    ):
        """Two spawns for same user but different projects should reuse allocation."""
        broker = _make_broker()
        client = MagicMock()

        # Setup mock allocation
        mock_alloc = MagicMock()
        mock_alloc.allocation_id = "alloc-1"
        mock_alloc.state = AllocationState.READY
        mock_alloc.start.return_value = True
        mock_alloc.get_shell_command.return_value = ["srun", "--overlap"]
        MockAllocation.return_value = mock_alloc

        # Setup mock shell
        mock_shell = MagicMock()
        mock_shell.spawn.return_value = True
        mock_shell.shell_id = "shell-1"
        MockShell.return_value = mock_shell

        msg1 = {
            "username": "alice",
            "project_slug": "proj-a",
            "container_path": "/opt/container.sif",
            "user_data_dir": "/data/alice",
            "project_dir": "/data/alice/proj/proj-a",
            "screen_session": "scitex-0",
        }

        result1 = handle_spawn_shared(broker, msg1, client)
        assert result1["status"] == "ok"

        # Allocation should be created once
        MockAllocation.assert_called_once()

        # Now spawn for same user, different project, different session
        msg2 = {
            "username": "alice",
            "project_slug": "proj-b",
            "container_path": "/opt/container.sif",
            "user_data_dir": "/data/alice",
            "project_dir": "/data/alice/proj/proj-b",
            "screen_session": "scitex-1",
        }

        # The existing allocation is now stored
        result2 = handle_spawn_shared(broker, msg2, client)
        assert result2["status"] == "ok"

        # Allocation should NOT be created a second time (reused)
        assert MockAllocation.call_count == 1


# ---------------------------------------------------------------------------
# Shell reattachment
# ---------------------------------------------------------------------------


class TestShellReattachment:
    """Existing running shell should be reattached, not spawned anew."""

    def test_reattach_existing_running_shell(self):
        broker = _make_broker()
        client = MagicMock()

        # Create an existing running shell
        existing_shell = MagicMock(spec=Shell)
        existing_shell.state = SessionState.RUNNING
        existing_shell.fd = 5
        existing_shell.get_scrollback.return_value = b""
        existing_shell.last_project_slug = "myproj"

        shell_id = "existing-shell-id"
        broker.shells[shell_id] = existing_shell
        broker.shell_index[("alice", "scitex-0")] = shell_id

        msg = {
            "username": "alice",
            "project_slug": "myproj",
            "container_path": "/opt/container.sif",
            "user_data_dir": "/data/alice",
            "project_dir": "/data/alice/proj/myproj",
            "screen_session": "scitex-0",
        }

        result = handle_spawn_shared(broker, msg, client)
        assert result["status"] == "ok"
        assert result["session_id"] == shell_id
        # Shell should be reattached, not newly spawned
        existing_shell.spawn.assert_not_called()

    def test_reattach_sends_cd_on_project_change(self):
        broker = _make_broker()
        client = MagicMock()

        existing_shell = MagicMock(spec=Shell)
        existing_shell.state = SessionState.RUNNING
        existing_shell.fd = 5
        existing_shell.get_scrollback.return_value = b""
        existing_shell.last_project_slug = "old-proj"

        shell_id = "existing-shell-id"
        broker.shells[shell_id] = existing_shell
        broker.shell_index[("alice", "scitex-0")] = shell_id

        msg = {
            "username": "alice",
            "project_slug": "new-proj",
            "container_path": "/opt/container.sif",
            "user_data_dir": "/data/alice",
            "project_dir": "/data/alice/proj/new-proj",
            "screen_session": "scitex-0",
        }

        handle_spawn_shared(broker, msg, client)
        # Should write cd command for project change
        existing_shell.write.assert_called()
        cd_call = existing_shell.write.call_args[0][0]
        assert b"cd /home/alice/proj/new-proj" in cd_call


# ---------------------------------------------------------------------------
# stop_allocation cleanup
# ---------------------------------------------------------------------------


class TestHandleStopAllocation:
    """handle_stop_allocation cleans up shells and stops allocation."""

    def test_stop_cleans_up_shells(self):
        broker = _make_broker()

        mock_alloc = MagicMock()
        mock_alloc.allocation_id = "alloc-1"
        broker.allocations["alloc-1"] = mock_alloc
        broker.alloc_index[("alice",)] = "alloc-1"

        mock_shell = MagicMock()
        mock_shell.allocation_id = "alloc-1"
        broker.shells["shell-1"] = mock_shell
        broker.shell_index[("alice", "scitex-0")] = "shell-1"

        result = handle_stop_allocation(
            broker, {"username": "alice", "project_slug": "myproj"}
        )
        assert result["status"] == "ok"
        mock_shell.close.assert_called_once()
        mock_alloc.stop.assert_called_once()
        assert "shell-1" not in broker.shells
        assert "alloc-1" not in broker.allocations

    def test_stop_nonexistent_returns_error(self):
        broker = _make_broker()
        result = handle_stop_allocation(
            broker, {"username": "nobody", "project_slug": "nope"}
        )
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# stop_all_allocations
# ---------------------------------------------------------------------------


class TestStopAllAllocations:
    """stop_all_allocations cleans up everything during broker shutdown."""

    def test_stops_all(self):
        broker = _make_broker()

        mock_shell = MagicMock()
        broker.shells["s1"] = mock_shell

        mock_alloc = MagicMock()
        broker.allocations["a1"] = mock_alloc
        broker.alloc_index[("alice",)] = "a1"

        stop_all_allocations(broker)
        mock_shell.close.assert_called_once()
        mock_alloc.stop.assert_called_once()
        assert len(broker.shells) == 0
        assert len(broker.allocations) == 0


# ---------------------------------------------------------------------------
# Cooldown logic
# ---------------------------------------------------------------------------


class TestAllocationCooldown:
    """After allocation failure, cooldown prevents immediate retry."""

    @patch(
        "apps.workspace.console_app.services.terminal_broker._handlers_shared._hard_fail_info"
    )
    def test_cooldown_returns_wait_message(self, mock_fail_info):
        broker = _make_broker()
        client = MagicMock()

        # Simulate recent failure — _hard_fail_info stores (timestamp, reason) tuples
        mock_fail_info.get.return_value = (
            time.time() - 5,
            "SLURM allocation failed",
        )  # 5s ago

        msg = {
            "username": "alice",
            "project_slug": "myproj",
            "container_path": "/opt/container.sif",
            "user_data_dir": "/data/alice",
            "project_dir": "/data/alice/proj/myproj",
            "screen_session": "scitex-0",
        }

        result = handle_spawn_shared(broker, msg, client)
        assert result["status"] == "error"
        assert "retrying in" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
