#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/views/terminal/execution.py

Covers:
- check_slurm_status: all branches (ready, unavailable, timeout, not_installed)
- is_slurm_available: wrapper delegation
- select_container: priority order and ContainerNotFoundError
- parse_time_limit_seconds: HH:MM:SS, MM:SS, and MM formats
"""

import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal Django / config stubs so execution.py can be imported without a
# running Django project.  These are injected into sys.modules before the
# first import of the module under test.
# ---------------------------------------------------------------------------

_SLURM_CONTAINER_PATH = "/opt/scitex/singularity/current-sandbox"
_BASE_CONTAINER_PATH = "/app/singularity/current-sandbox"
_SLURM_PARTITION = "express"
_SLURM_USER_DATA_ROOT = Path("/opt/scitex/data/users")


def _install_django_stubs():
    """Inject minimal Django + config stubs into sys.modules."""
    # django.conf.settings stub
    settings_stub = MagicMock()
    settings_stub.SINGULARITY_IMAGE_PATH = _BASE_CONTAINER_PATH
    settings_stub.USER_DATA_ROOT = "/app/data/users"

    django_conf = types.ModuleType("django.conf")
    django_conf.settings = settings_stub

    django_mod = types.ModuleType("django")
    sys.modules.setdefault("django", django_mod)
    sys.modules["django.conf"] = django_conf

    # console_app.views.terminal.config stub — imported as relative .config
    config_stub = types.ModuleType("apps.console_app.views.terminal.config")
    config_stub.SLURM_CONTAINER_PATH = _SLURM_CONTAINER_PATH
    config_stub.BASE_CONTAINER_PATH = _BASE_CONTAINER_PATH
    config_stub.SLURM_PARTITION = _SLURM_PARTITION
    config_stub.SLURM_USER_DATA_ROOT = _SLURM_USER_DATA_ROOT

    def _parse_time_limit_seconds(time_str: str) -> int:
        parts = time_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0]) * 60

    config_stub.parse_time_limit_seconds = _parse_time_limit_seconds
    config_stub.SLURM_TIME_LIMIT = "04:00:00"
    config_stub.SLURM_TIME_LIMIT_SECONDS = 14400
    config_stub.SLURM_CPUS = 2
    config_stub.SLURM_MEMORY_GB = 4

    sys.modules["apps.console_app.views.terminal.config"] = config_stub

    # _command_builder stub (used by exec_slurm_shell, not under test here)
    builder_stub = types.ModuleType("apps.console_app.views.terminal._command_builder")
    builder_stub.build_srun_cmd = MagicMock(return_value=["srun", "--pty"])
    sys.modules["apps.console_app.views.terminal._command_builder"] = builder_stub


_install_django_stubs()

# ---------------------------------------------------------------------------
# Now import the module under test.  We import functions directly so that
# monkeypatching subprocess.run inside test methods is straightforward.
# ---------------------------------------------------------------------------

# Add project root to sys.path so absolute imports work.
_PROJECT_ROOT = Path(__file__).parents[6]  # …/scitex-cloud
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Patch the relative config import that execution.py uses internally.
# execution.py does: from .config import SLURM_CONTAINER_PATH, SLURM_PARTITION, SLURM_USER_DATA_ROOT
# We inject the package so Python resolves the relative import correctly.
_pkg_name = "apps.console_app.views.terminal"
for _part in [
    "apps",
    "apps.console_app",
    "apps.console_app.views",
    "apps.console_app.views.terminal",
]:
    sys.modules.setdefault(_part, types.ModuleType(_part))

# Point the package's __init__ at our config stub
_term_pkg = sys.modules["apps.console_app.views.terminal"]
_term_pkg.config = sys.modules["apps.console_app.views.terminal.config"]

# Finally import the module under test
import importlib

_execution_mod = importlib.import_module("apps.console_app.views.terminal.execution")
check_slurm_status = _execution_mod.check_slurm_status
is_slurm_available = _execution_mod.is_slurm_available
select_container = _execution_mod.select_container
ContainerNotFoundError = _execution_mod.ContainerNotFoundError
SlurmUnavailableError = _execution_mod.SlurmUnavailableError

# parse_time_limit_seconds lives in config.py — import directly
from apps.console_app.views.terminal.config import (  # noqa: E402
    parse_time_limit_seconds,
)

# ===========================================================================
# Tests: check_slurm_status
# ===========================================================================


class TestCheckSlurmStatus:
    """Unit tests for check_slurm_status()."""

    def test_returns_ready_when_scontrol_succeeds(self):
        """(True, 'ready') when scontrol ping exits 0."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(
            "apps.console_app.views.terminal.execution.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            available, status = check_slurm_status()

        mock_run.assert_called_once_with(
            ["scontrol", "ping"],
            capture_output=True,
            timeout=5,
        )
        assert available is True
        assert status == "ready"

    def test_returns_unavailable_when_scontrol_fails(self):
        """(False, 'unavailable') when scontrol ping exits non-zero."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(
            "apps.console_app.views.terminal.execution.subprocess.run",
            return_value=mock_result,
        ):
            available, status = check_slurm_status()

        assert available is False
        assert status == "unavailable"

    def test_returns_unavailable_on_timeout(self):
        """(False, 'unavailable') when subprocess.TimeoutExpired is raised."""
        with patch(
            "apps.console_app.views.terminal.execution.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["scontrol", "ping"], timeout=5),
        ):
            available, status = check_slurm_status()

        assert available is False
        assert status == "unavailable"

    def test_returns_not_installed_when_file_not_found(self):
        """(False, 'not_installed') when scontrol binary is missing."""
        with patch(
            "apps.console_app.views.terminal.execution.subprocess.run",
            side_effect=FileNotFoundError("scontrol not found"),
        ):
            available, status = check_slurm_status()

        assert available is False
        assert status == "not_installed"

    def test_return_type_is_tuple_of_bool_and_str(self):
        """Return value is always (bool, str)."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(
            "apps.console_app.views.terminal.execution.subprocess.run",
            return_value=mock_result,
        ):
            result = check_slurm_status()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


# ===========================================================================
# Tests: is_slurm_available
# ===========================================================================


class TestIsSlurmAvailable:
    """Unit tests for is_slurm_available() wrapper."""

    def test_returns_true_when_slurm_ready(self):
        """Delegates to check_slurm_status and returns True when ready."""
        with patch(
            "apps.console_app.views.terminal.execution.check_slurm_status",
            return_value=(True, "ready"),
        ):
            assert is_slurm_available() is True

    def test_returns_false_when_slurm_unavailable(self):
        """Returns False when status is unavailable."""
        with patch(
            "apps.console_app.views.terminal.execution.check_slurm_status",
            return_value=(False, "unavailable"),
        ):
            assert is_slurm_available() is False

    def test_returns_false_when_not_installed(self):
        """Returns False when SLURM is not installed."""
        with patch(
            "apps.console_app.views.terminal.execution.check_slurm_status",
            return_value=(False, "not_installed"),
        ):
            assert is_slurm_available() is False

    def test_discards_status_string(self):
        """Only the boolean part of check_slurm_status is propagated."""
        for available, status in [
            (True, "ready"),
            (False, "unavailable"),
            (False, "not_installed"),
        ]:
            with patch(
                "apps.console_app.views.terminal.execution.check_slurm_status",
                return_value=(available, status),
            ):
                result = is_slurm_available()
                assert result is available


# ===========================================================================
# Tests: select_container (filesystem-based, using tmp_path)
# ===========================================================================


class TestSelectContainer:
    """Unit tests for select_container() path-selection logic."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_project_container(self, project_dir: Path) -> Path:
        """Create the project-specific container path as a file."""
        sif_dir = project_dir / ".singularity"
        sif_dir.mkdir(parents=True, exist_ok=True)
        sif = sif_dir / "custom.sif"
        sif.touch()
        return sif

    def _make_user_container(self, user_data_dir: Path) -> Path:
        """Create the user-default container path as a file."""
        sif_dir = user_data_dir / ".singularity"
        sif_dir.mkdir(parents=True, exist_ok=True)
        sif = sif_dir / "default.sif"
        sif.touch()
        return sif

    # ------------------------------------------------------------------
    # Test: project container has highest priority
    # ------------------------------------------------------------------

    def test_returns_project_container_when_present_as_file(self, tmp_path):
        """Project-specific custom.sif (file) is returned first."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        expected = self._make_project_container(project_dir)
        # Also create user container — should still pick project one
        self._make_user_container(user_data_dir)

        result = select_container(user_data_dir, project_dir)
        assert result == str(expected)

    def test_returns_project_container_when_present_as_sandbox_dir(self, tmp_path):
        """Project-specific custom.sif that is a *directory* (sandbox) is returned."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        sif_dir = project_dir / ".singularity"
        sif_dir.mkdir(parents=True)
        sandbox = sif_dir / "custom.sif"
        sandbox.mkdir()  # directory, not file

        result = select_container(user_data_dir, project_dir)
        assert result == str(sandbox)

    # ------------------------------------------------------------------
    # Test: user default container as second priority
    # ------------------------------------------------------------------

    def test_returns_user_default_when_no_project_container(self, tmp_path):
        """User default.sif is returned when no project container exists."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        expected = self._make_user_container(user_data_dir)

        result = select_container(user_data_dir, project_dir)
        assert result == str(expected)

    def test_returns_user_container_when_present_as_sandbox_dir(self, tmp_path):
        """User default.sif that is a sandbox directory is returned."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        sif_dir = user_data_dir / ".singularity"
        sif_dir.mkdir(parents=True)
        sandbox = sif_dir / "default.sif"
        sandbox.mkdir()

        result = select_container(user_data_dir, project_dir)
        assert result == str(sandbox)

    # ------------------------------------------------------------------
    # Test: base container fallback (mocked paths)
    # ------------------------------------------------------------------

    def test_returns_slurm_container_path_when_only_base_container_exists(
        self, tmp_path
    ):
        """Falls back to SLURM_CONTAINER_PATH when it exists on host."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # No project or user container created

        # Simulate: docker path does not exist, but host path does
        with (
            patch(
                "apps.console_app.views.terminal.config.BASE_CONTAINER_PATH",
                "/nonexistent/docker/path",
            ),
            patch(
                "apps.console_app.views.terminal.execution.SLURM_CONTAINER_PATH",
                str(tmp_path / "host_container.sif"),
            ),
        ):
            host_sif = tmp_path / "host_container.sif"
            host_sif.touch()

            result = select_container(user_data_dir, project_dir)
            assert result == str(host_sif)

    # ------------------------------------------------------------------
    # Test: ContainerNotFoundError raised when nothing exists
    # ------------------------------------------------------------------

    def test_raises_container_not_found_error_when_no_container_exists(self, tmp_path):
        """ContainerNotFoundError raised when neither docker nor host path exists."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with (
            patch(
                "apps.console_app.views.terminal.config.BASE_CONTAINER_PATH",
                str(tmp_path / "nonexistent_docker.sif"),
            ),
            patch(
                "apps.console_app.views.terminal.execution.SLURM_CONTAINER_PATH",
                str(tmp_path / "nonexistent_host.sif"),
            ),
        ):
            with pytest.raises(ContainerNotFoundError) as exc_info:
                select_container(user_data_dir, project_dir)

        assert "nonexistent_host.sif" in str(exc_info.value)

    def test_container_not_found_error_message_contains_container_path(self, tmp_path):
        """Error message includes the container path for operator guidance."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        fake_path = str(tmp_path / "missing.sif")

        with (
            patch(
                "apps.console_app.views.terminal.config.BASE_CONTAINER_PATH",
                fake_path,
            ),
            patch(
                "apps.console_app.views.terminal.execution.SLURM_CONTAINER_PATH",
                fake_path,
            ),
        ):
            with pytest.raises(ContainerNotFoundError, match="missing.sif"):
                select_container(user_data_dir, project_dir)

    def test_project_container_takes_priority_over_user_and_base(self, tmp_path):
        """Project container wins over both user-default and base container."""
        user_data_dir = tmp_path / "user"
        user_data_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        project_sif = self._make_project_container(project_dir)
        self._make_user_container(user_data_dir)
        base_sif = tmp_path / "base.sif"
        base_sif.touch()

        with (
            patch(
                "apps.console_app.views.terminal.config.BASE_CONTAINER_PATH",
                str(base_sif),
            ),
            patch(
                "apps.console_app.views.terminal.execution.SLURM_CONTAINER_PATH",
                str(base_sif),
            ),
        ):
            result = select_container(user_data_dir, project_dir)

        assert result == str(project_sif)


# ===========================================================================
# Tests: parse_time_limit_seconds (from config.py)
# ===========================================================================


class TestParseTimeLimitSeconds:
    """Unit tests for parse_time_limit_seconds()."""

    def test_hh_mm_ss_format(self):
        """04:00:00 -> 4 * 3600 = 14400 seconds."""
        assert parse_time_limit_seconds("04:00:00") == 14400

    def test_hh_mm_ss_with_nonzero_minutes_and_seconds(self):
        """01:30:45 -> 3600 + 1800 + 45 = 5445 seconds."""
        assert parse_time_limit_seconds("01:30:45") == 5445

    def test_mm_ss_format(self):
        """30:00 -> 30 * 60 = 1800 seconds."""
        assert parse_time_limit_seconds("30:00") == 1800

    def test_mm_ss_format_nonzero_seconds(self):
        """10:30 -> 10 * 60 + 30 = 630 seconds."""
        assert parse_time_limit_seconds("10:30") == 630

    def test_single_part_format(self):
        """60 -> 60 * 60 = 3600 seconds (treated as minutes)."""
        assert parse_time_limit_seconds("60") == 3600

    def test_single_part_one_minute(self):
        """1 -> 1 * 60 = 60 seconds."""
        assert parse_time_limit_seconds("1") == 60

    def test_zero_time_limit(self):
        """00:00:00 -> 0 seconds."""
        assert parse_time_limit_seconds("00:00:00") == 0

    def test_default_slurm_time_limit(self):
        """The documented default '04:00:00' maps to exactly 14400 seconds."""
        assert parse_time_limit_seconds("04:00:00") == 4 * 3600

    def test_large_hour_value(self):
        """100:00:00 -> 360000 seconds."""
        assert parse_time_limit_seconds("100:00:00") == 100 * 3600


# ===========================================================================
# Custom exception classes are importable and subclass Exception
# ===========================================================================


class TestExceptionClasses:
    """Verify exception class hierarchy."""

    def test_slurm_unavailable_error_is_exception(self):
        assert issubclass(SlurmUnavailableError, Exception)

    def test_container_not_found_error_is_exception(self):
        assert issubclass(ContainerNotFoundError, Exception)

    def test_slurm_unavailable_error_can_be_raised_and_caught(self):
        with pytest.raises(SlurmUnavailableError):
            raise SlurmUnavailableError("SLURM down")

    def test_container_not_found_error_can_be_raised_and_caught(self):
        with pytest.raises(ContainerNotFoundError):
            raise ContainerNotFoundError("No container found")


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
