#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/smoke/test_cli_smoke.py

"""Smoke layer (PS-211): fast subprocess CLI happy-path tests.

Each test shells out to the real ``scitex-hub`` console script beside
the running interpreter and asserts on exit code + output — no mocks,
no Django, no database. Must stay under 60 s total; ``--version`` and
``--help`` both return in well under a second.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

CONSOLE_SCRIPT = Path(sys.executable).with_name("scitex-hub")

requires_console_script = pytest.mark.skipif(
    not CONSOLE_SCRIPT.is_file(),
    reason="no scitex-hub console script beside this interpreter",
)


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    """Run the console script, capturing text output."""
    return subprocess.run(
        [str(CONSOLE_SCRIPT), *argv],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@requires_console_script
@pytest.mark.smoke
def test_version_reports_the_package_version():
    """``scitex-hub --version`` exits 0 and names the installed version."""
    # Arrange
    import scitex_hub

    # Act
    completed = _run("--version")
    # Assert
    assert (completed.returncode, scitex_hub.__version__ in completed.stdout) == (
        0,
        True,
    ), completed.stderr


@requires_console_script
@pytest.mark.smoke
def test_help_lists_the_top_level_commands():
    """``scitex-hub --help`` exits 0 and shows the command surface."""
    # Arrange
    argv = ("--help",)
    # Act
    completed = _run(*argv)
    # Assert
    assert (completed.returncode, "dev-preview" in completed.stdout) == (
        0,
        True,
    ), completed.stderr
