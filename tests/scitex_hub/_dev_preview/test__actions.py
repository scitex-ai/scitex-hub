#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_dev_preview/test__actions.py

"""Every way an action can fail surfaces as :class:`ActionFailed`, never a crash.

The sync engine records an attempt only for the exception classes it knows;
before 2026-09-05 ``health_status`` let a missing ``docker`` binary escape as
``FileNotFoundError`` and a hung inspect as ``TimeoutExpired``, so the
designed HOLD became a rebuild every 2 minutes with nothing on the board.
These tests run the real ``wait_healthy`` against a real (empty) ``PATH``
— no mock library — and pin that the failure is typed and carries the exit
code the log legend documents (127: could not start).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

from scitex_hub._dev_preview import ActionFailed
from scitex_hub._dev_preview._actions import wait_healthy


@pytest.fixture
def empty_path(tmp_path: Path) -> Iterator[Path]:
    """A ``PATH`` with no ``docker`` in it (real env var, restored on teardown)."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    previous = os.environ.get("PATH")
    os.environ["PATH"] = str(empty)
    yield empty
    if previous is None:
        os.environ.pop("PATH", None)
    else:
        os.environ["PATH"] = previous


def test_missing_docker_binary_is_a_typed_action_failure(empty_path: Path):
    """No ``docker`` on PATH must be recorded by the engine, not crash past its gate."""
    # Arrange
    container = "scitex-hub-dev-django-1"
    # Act — anything other than ActionFailed propagates and ERRORS the test,
    # which is exactly the escape this pins against
    try:
        wait_healthy(container, timeout=1)
        outcome: tuple[str, int | None] = ("returned", None)
    except ActionFailed as exc:
        outcome = (exc.action, exc.rc)
    # Assert
    assert outcome == ("wait_healthy", 127)


# EOF
