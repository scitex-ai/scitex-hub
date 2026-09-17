#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The cursor is decoration: a stale target must cost the glide and nothing else.

Measured 2026-09-17: a signed-in render died at the "open a file" step with
`Locator.scroll_into_view_if_needed: Element is not attached to the DOM`, because the
project tree re-renders right after a project is created and the row the cursor was
aiming at had been replaced. The click that follows would have auto-waited for the new
row; the cosmetic glide took the whole render down instead.
"""

import sys
from pathlib import Path

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_cursor import MovingCursor  # noqa: E402


class FakeMouse:
    def __init__(self):
        self.moves = []

    def move(self, x, y):
        self.moves.append((x, y))


class FakePage:
    def __init__(self):
        self.mouse = FakeMouse()
        self.waits = []

    def wait_for_timeout(self, milliseconds):
        self.waits.append(milliseconds)


class DetachedLocator:
    """What Playwright raises when the element was re-rendered under you."""

    def scroll_into_view_if_needed(self, timeout=None):
        raise Exception("Locator.scroll_into_view_if_needed: Element is not attached to the DOM")

    def bounding_box(self):
        raise AssertionError("must not be reached after a failed scroll")


class BoundlessLocator:
    """An element with no box (hidden, or mid-animation)."""

    def scroll_into_view_if_needed(self, timeout=None):
        return None

    def bounding_box(self):
        return None


class RealLocator:
    def __init__(self, box):
        self.box = box

    def scroll_into_view_if_needed(self, timeout=None):
        return None

    def bounding_box(self):
        return self.box


def test_a_detached_target_does_not_raise_and_does_not_move():
    # Arrange
    page = FakePage()
    cursor = MovingCursor(page, 1280, 720)
    start = (cursor.x, cursor.y)
    # Act: this used to abort the render.
    cursor.glide_to(DetachedLocator())
    # Assert
    assert (cursor.x, cursor.y) == start
    assert page.mouse.moves == []


def test_a_target_without_a_box_is_skipped_quietly():
    # Arrange
    page = FakePage()
    cursor = MovingCursor(page, 1280, 720)
    # Act
    cursor.glide_to(BoundlessLocator())
    # Assert
    assert page.mouse.moves == []


def test_a_present_target_still_glides_and_lands_on_its_centre():
    # Arrange
    page = FakePage()
    cursor = MovingCursor(page, 1280, 720)
    locator = RealLocator({"x": 100.0, "y": 200.0, "width": 40.0, "height": 20.0})
    # Act
    cursor.glide_to(locator, duration_seconds=0.01)
    # Assert
    assert len(page.mouse.moves) >= 8
    assert (cursor.x, cursor.y) == (120.0, 210.0)
    assert page.mouse.moves[-1] == (120.0, 210.0)
