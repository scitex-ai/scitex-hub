#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notifications link to the entry, because a file sent to chat disappears."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "apps" / "infra" / "public_app"))

from clip_registry import ClipError, entry_url, notification_line  # noqa: E402


def test_the_entry_url_points_at_that_entry_on_the_index():
    # Arrange / Act / Assert
    assert entry_url("projects-2026-09-17-45f607f7") == \
        "/internal/demos/#entry-projects-2026-09-17-45f607f7"
    assert entry_url("x", "https://hub.example") == "https://hub.example/internal/demos/#entry-x"
    assert entry_url("x", "https://hub.example/") == "https://hub.example/internal/demos/#entry-x"


def test_a_notification_line_carries_the_status_and_the_link():
    # Arrange / Act
    line = notification_line("projects-2026-09-17-9658829c", status="rejected")
    # Assert
    assert "projects-2026-09-17-9658829c" in line
    assert "rejected" in line
    assert line.endswith("/internal/demos/#entry-projects-2026-09-17-9658829c")


def test_a_link_without_an_entry_is_refused():
    # Arrange / Act / Assert: an update with no entry to point at is the problem, not a fix.
    with pytest.raises(ClipError):
        entry_url("")
    with pytest.raises(ClipError):
        notification_line("")
