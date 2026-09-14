#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""At 1920x1080 the page frame is ~90% of the viewport and centred; at 390 nothing scrolls sideways.

Operator 2026-09-14: large displays should keep whitespace margins left and
right instead of spreading content edge to edge. The frame is the outermost
layout box a page renders: the workspace shell, scitex-ui's standalone shell
(Scholar v2), or <main> on plain pages. The CSS source is pinned by
tests/templates/test_site_content_frame.py.

One assertion per test.
"""

import pytest
from tests.e2e.playwright.conftest import TEST_USER
from tests.e2e.playwright.page_ready import wait_for_page_ready

FRAME_RATIO = 0.90
RATIO_TOLERANCE = 0.02
CENTRING_TOLERANCE_PX = 24

PAGES = [
    "/",
    "/pricing/",
    "/accounts/settings/",
    f"/{TEST_USER}/dotfiles/",
    "/apps/scholar/v2/",
    "/apps/docs/",
]

_FRAME_PROBE = """() => {
  const frame = document.querySelector('#workspace-layout')
    || document.querySelector('#workspace-three-col')
    || document.querySelector('body > #main-content');
  const box = frame.getBoundingClientRect();
  const viewport = window.innerWidth;
  return {
    viewport: viewport,
    width: box.width,
    left_margin: box.left,
    right_margin: viewport - box.right,
    scroll_width: document.documentElement.scrollWidth,
    client_width: document.documentElement.clientWidth,
  };
}"""


def _probe(page, path):
    page.goto(path)
    wait_for_page_ready(page, hydration_signal=False)
    return page.evaluate(_FRAME_PROBE)


@pytest.mark.parametrize("path", PAGES)
def test_desktop_frame_is_ninety_percent_of_the_viewport(visitor_desktop_page, path):
    # Arrange
    page = visitor_desktop_page

    # Act
    frame = _probe(page, path)

    # Assert
    assert abs(frame["width"] / frame["viewport"] - FRAME_RATIO) <= RATIO_TOLERANCE, frame


@pytest.mark.parametrize("path", PAGES)
def test_desktop_frame_is_centred(visitor_desktop_page, path):
    # Arrange
    page = visitor_desktop_page

    # Act
    frame = _probe(page, path)

    # Assert
    assert abs(frame["left_margin"] - frame["right_margin"]) <= CENTRING_TOLERANCE_PX, frame


@pytest.mark.parametrize("path", PAGES)
def test_phone_page_has_no_horizontal_scroll(visitor_mobile_page, path):
    # Arrange
    page = visitor_mobile_page

    # Act
    frame = _probe(page, path)

    # Assert
    assert frame["scroll_width"] <= frame["client_width"], frame
