#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/services/terminal_broker/allocation.py

Tests failure reason formatting, remaining seconds, shell counting,
and state transitions.
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.console_app.services.terminal_broker.allocation import (
    Allocation,
    AllocationState,
)

# ---------------------------------------------------------------------------
# AllocationState
# ---------------------------------------------------------------------------


class TestAllocationState:
    """AllocationState enum values."""

    def test_starting_value(self):
        assert AllocationState.STARTING.value == "starting"

    def test_ready_value(self):
        assert AllocationState.READY.value == "ready"

    def test_stopping_value(self):
        assert AllocationState.STOPPING.value == "stopping"

    def test_dead_value(self):
        assert AllocationState.DEAD.value == "dead"


# ---------------------------------------------------------------------------
# Allocation init
# ---------------------------------------------------------------------------


class TestAllocationInit:
    """Allocation initializes with correct defaults."""

    def _make_alloc(self):
        return Allocation(
            username="alice",
            project_slug="myproj",
            container_path="/opt/container.sif",
            host_user_dir=Path("/data/alice"),
            host_project_dir=Path("/data/alice/proj/myproj"),
        )

    def test_initial_state_is_dead(self):
        alloc = self._make_alloc()
        assert alloc.state == AllocationState.DEAD

    def test_initial_shell_count_zero(self):
        alloc = self._make_alloc()
        assert alloc.shell_count == 0

    def test_initial_job_id_none(self):
        alloc = self._make_alloc()
        assert alloc.job_id is None

    def test_instance_name_contains_username(self):
        alloc = self._make_alloc()
        assert alloc.instance_name == "scitex-alice"

    def test_allocation_id_is_uuid(self):
        alloc = self._make_alloc()
        assert len(alloc.allocation_id) == 36  # UUID format


# ---------------------------------------------------------------------------
# Shell counting
# ---------------------------------------------------------------------------


class TestShellCounting:
    """increment_shells / decrement_shells track active shells."""

    def _make_alloc(self):
        return Allocation(
            username="alice",
            project_slug="myproj",
            container_path="/opt/container.sif",
            host_user_dir=Path("/data/alice"),
            host_project_dir=Path("/data/alice/proj/myproj"),
        )

    def test_increment(self):
        alloc = self._make_alloc()
        alloc.increment_shells()
        assert alloc.shell_count == 1

    def test_decrement(self):
        alloc = self._make_alloc()
        alloc.shell_count = 3
        alloc.decrement_shells()
        assert alloc.shell_count == 2

    def test_decrement_does_not_go_negative(self):
        alloc = self._make_alloc()
        alloc.decrement_shells()
        assert alloc.shell_count == 0

    def test_multiple_increments(self):
        alloc = self._make_alloc()
        for _ in range(5):
            alloc.increment_shells()
        assert alloc.shell_count == 5


# ---------------------------------------------------------------------------
# Remaining seconds
# ---------------------------------------------------------------------------


class TestGetRemainingSeconds:
    """get_remaining_seconds calculates time left in allocation."""

    def _make_alloc(self, time_limit=3600):
        alloc = Allocation(
            username="alice",
            project_slug="myproj",
            container_path="/opt/container.sif",
            host_user_dir=Path("/data/alice"),
            host_project_dir=Path("/data/alice/proj/myproj"),
            time_limit_seconds=time_limit,
        )
        return alloc

    def test_returns_none_when_not_started(self):
        alloc = self._make_alloc()
        assert alloc.get_remaining_seconds() is None

    def test_returns_none_when_dead(self):
        alloc = self._make_alloc()
        alloc.started_at = time.time()
        alloc.state = AllocationState.DEAD
        assert alloc.get_remaining_seconds() is None

    def test_returns_remaining_when_ready(self):
        alloc = self._make_alloc(time_limit=3600)
        alloc.state = AllocationState.READY
        alloc.started_at = time.time() - 1000  # 1000s elapsed
        remaining = alloc.get_remaining_seconds()
        assert remaining is not None
        assert 2590 <= remaining <= 2610  # ~2600s remaining

    def test_returns_zero_when_expired(self):
        alloc = self._make_alloc(time_limit=100)
        alloc.state = AllocationState.READY
        alloc.started_at = time.time() - 200  # expired
        assert alloc.get_remaining_seconds() == 0


# ---------------------------------------------------------------------------
# Failure reason formatting
# ---------------------------------------------------------------------------


class TestFormatFailureReason:
    """_format_failure_reason maps SLURM states to human messages."""

    def test_timeout(self):
        msg = Allocation._format_failure_reason("TIMEOUT", "")
        assert "time limit" in msg.lower()

    def test_cancelled(self):
        msg = Allocation._format_failure_reason("CANCELLED", "")
        assert "stopped" in msg.lower()

    def test_failed(self):
        msg = Allocation._format_failure_reason("FAILED", "")
        assert "error" in msg.lower()

    def test_node_fail(self):
        msg = Allocation._format_failure_reason("NODE_FAIL", "")
        assert "server" in msg.lower() or "restarting" in msg.lower()

    def test_preempted(self):
        msg = Allocation._format_failure_reason("PREEMPTED", "")
        assert "restarting" in msg.lower()

    def test_out_of_memory(self):
        msg = Allocation._format_failure_reason("OUT_OF_MEMORY", "")
        assert "memory" in msg.lower()

    def test_unknown_state(self):
        msg = Allocation._format_failure_reason("SOMETHING_ELSE", "")
        assert "ended" in msg.lower()


# ---------------------------------------------------------------------------
# check_alive
# ---------------------------------------------------------------------------


class TestCheckAlive:
    """check_alive queries squeue for job state."""

    def _make_alloc(self):
        alloc = Allocation(
            username="alice",
            project_slug="myproj",
            container_path="/opt/container.sif",
            host_user_dir=Path("/data/alice"),
            host_project_dir=Path("/data/alice/proj/myproj"),
        )
        alloc.job_id = "12345"
        return alloc

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_alive_when_running(self, mock_run):
        mock_run.return_value = MagicMock(stdout="RUNNING\n", returncode=0)
        alloc = self._make_alloc()
        assert alloc.check_alive() is True

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_alive_when_pending(self, mock_run):
        mock_run.return_value = MagicMock(stdout="PENDING\n", returncode=0)
        alloc = self._make_alloc()
        assert alloc.check_alive() is True

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_dead_when_completed(self, mock_run):
        mock_run.return_value = MagicMock(stdout="COMPLETED\n", returncode=0)
        alloc = self._make_alloc()
        assert alloc.check_alive() is False

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_dead_when_empty(self, mock_run):
        mock_run.return_value = MagicMock(stdout="\n", returncode=0)
        alloc = self._make_alloc()
        assert alloc.check_alive() is False

    def test_dead_when_no_job_id(self):
        alloc = self._make_alloc()
        alloc.job_id = None
        assert alloc.check_alive() is False

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_dead_on_exception(self, mock_run):
        mock_run.side_effect = Exception("squeue failed")
        alloc = self._make_alloc()
        assert alloc.check_alive() is False


# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------


class TestAllocationStop:
    """stop() cancels job and transitions to DEAD."""

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_stop_sets_dead(self, mock_run):
        alloc = Allocation(
            username="alice",
            project_slug="myproj",
            container_path="/opt/container.sif",
            host_user_dir=Path("/data/alice"),
            host_project_dir=Path("/data/alice/proj/myproj"),
        )
        alloc.job_id = "12345"
        alloc.state = AllocationState.READY
        alloc.stop()
        assert alloc.state == AllocationState.DEAD

    @patch("apps.console_app.services.terminal_broker.allocation.subprocess.run")
    def test_stop_calls_scancel(self, mock_run):
        alloc = Allocation(
            username="alice",
            project_slug="myproj",
            container_path="/opt/container.sif",
            host_user_dir=Path("/data/alice"),
            host_project_dir=Path("/data/alice/proj/myproj"),
        )
        alloc.job_id = "12345"
        alloc.state = AllocationState.READY
        alloc.stop()
        mock_run.assert_called_once()
        assert "scancel" in mock_run.call_args[0][0]


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
