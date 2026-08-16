#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture a light-mode screenshot of every page worth showing someone.

WHY THIS EXISTS. The operator asked for the screenshots to be CI'd rather
than taken by hand: 「スクショをci化して欲しいです」. Hand-taken shots go
stale the moment anything ships, and the moment you need them — a grant
application, a talk, a README — is exactly when you do not want to be
clicking through the product hoping nothing is broken.

TWO JOBS IN ONE RUN:

  1. A downloadable set of current product screenshots, as a CI artifact.
     Grab the artifact, drop the PNGs into the document.
  2. A smoke test. Every page here must return HTTP 200 and render its
     shell. A page that started 500ing, or that renders blank, fails the
     job — so a broken screen is caught by the thing that photographs it
     rather than discovered while assembling a submission.

LIGHT MODE, deliberately. The operator: 「スライドだからさあ」 — these go
on slides, where the dark theme reads badly. The site stores the theme
per user and serves dark by default, so each page sets
``data-theme="light"`` on <html> before the shot. Verified against
production: that flips body from rgb(13,17,23) to rgb(250,249,247).

A VISITOR SESSION, deliberately. These run as the pooled visitor, not as a
real account, so nothing in the artifact can contain anybody's private
project, manuscript or chat history. A screenshot artifact is downloadable
by anyone who can read the run; it must never carry real user data.

FULL PAGE, deliberately: ``screenshot(..., full_page=True)`` in the shared
fixture, so a long page is captured whole rather than cropped at the fold.
"""

from __future__ import annotations

import pytest

# (route, slug, what a human would call it)
#
# The operator named the set he actually shows people: the apps home, a
# project page, Writer, Scholar, FigRecipe, Tools and the App Store
# ("App Storeは絶対見せる"), plus Cards and Chat. Adding a page here is one
# line and it is picked up by both jobs.
PAGES = [
    ("/", "00-workspace-home", "Workspace home"),
    ("/apps/home/", "01-projects", "Projects"),
    ("/apps/writer/", "02-writer", "Writer"),
    ("/apps/scholar/", "03-scholar", "Scholar"),
    ("/apps/figrecipe/", "04-figrecipe", "FigRecipe"),
    ("/apps/tools/", "05-tools", "Tools"),
    ("/apps/store/", "06-app-store", "App Store"),
    ("/apps/cards/", "07-cards", "Cards"),
    ("/chat/", "08-chat", "Chat"),
    ("/apps/docs/", "09-docs", "Docs"),
    ("/landing/", "10-landing", "Landing"),
]

FORCE_LIGHT = """
() => {
  document.documentElement.setAttribute('data-theme', 'light');
  document.documentElement.style.colorScheme = 'light';
}
"""


@pytest.mark.parametrize(
    "route,slug,title", PAGES, ids=[p[1] for p in PAGES]
)
class TestProductScreenshots:
    def test_page_is_served(self, visitor_desktop_page, route, slug, title):
        # Arrange
        page = visitor_desktop_page

        # Act
        response = page.goto(route)

        # Assert — a redirect is fine (sign-in walls, canonical paths);
        # a server error is not, and is what this is here to catch.
        status = response.status if response else 0
        assert status < 400, f"{title} ({route}) returned HTTP {status}"

    def test_page_renders_and_is_captured(
        self, visitor_desktop_page, screenshot, route, slug, title
    ):
        # Arrange
        page = visitor_desktop_page
        page.goto(route)
        # networkidle rather than load: these pages hydrate after load, and
        # photographing them too early captures empty containers. Measured
        # 2026-08-16 — reading a page mid-hydration produced four false
        # "this is broken" reports in one session.
        page.wait_for_load_state("networkidle")
        page.evaluate(FORCE_LIGHT)

        # Act
        screenshot(page, slug)
        body_text = page.evaluate("() => (document.body.innerText || '').trim()")

        # Assert — a page that renders no visible text at all is broken,
        # and a blank PNG in the artifact would hide that.
        assert body_text, f"{title} ({route}) rendered no visible text"
