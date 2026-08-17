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

A VISITOR SESSION, deliberately — AND CHECKED, not merely asserted in
prose. These run as the pooled visitor, not as a real account, so nothing
in the artifact can contain anybody's private project, manuscript or chat
history. A screenshot artifact is downloadable by anyone who can read the
run; it must never carry real user data.

That sentence used to be the whole guarantee. It is now enforced twice:
the ``pooled_visitor_page`` fixture refuses to hand out a page unless the
session really is a writable pool slot, and every page below re-reads
``body[data-session-role]`` after navigating. Neither of the original
failure conditions could see this: when the pool has no verified-clean
slot, allocation falls back to the SHARED readonly-visitor account, which
returns 200 and renders a full page — so HTTP<400 passes, non-blank text
passes, and the artifact quietly shows the wrong product. Both CI (broken
Gitea credential, this PR) and production (15/16 slots quarantined) were
measured in exactly that state on 2026-08-16.

FULL PAGE, deliberately: ``screenshot(..., full_page=True)`` in the shared
fixture, so a long page is captured whole rather than cropped at the fold.
"""

from __future__ import annotations

import pytest

from tests.e2e.playwright.content_check import (
    PAGE_ELEMENT_SIGNALS,
    BrowserProblemLog,
    body_text_problem,
    broken_image_problem,
    describe_browser_problems,
    describe_signals,
    empty_container_problem,
    loading_marker_problem,
    nonzero_count_problem,
    read_content_signals,
    stuck_placeholder_problem,
    undeclared_absent_media_problem,
)
from tests.e2e.playwright.page_ready import wait_for_page_ready
from tests.e2e.playwright.session_role_check import (
    READ_SESSION_ROLE_JS,
    REQUIRED_ROLE,
    VISITOR_WARMUP_ROUTE,
    wrong_role_message,
)

# Routes whose response does NOT extend templates/global_base.html, and so
# carry neither `body.app-ready` nor `body[data-session-role]`.
#
# Measured 2026-08-16 against a live server: GET /apps/cards/ returns 200 and
# 195 KB of HTML titled "SciTeX Cards v0.42.0" with ZERO occurrences of the
# global_base loading-screen markup, while /apps/docs/ has four. It is the
# embedded Cards board, rendered by its own template.
#
# This is a DECLARATION, not an exemption. The session identity belongs to
# the browser context, not to one page's markup, so the check does not
# disappear for these routes — it is taken on the warm-up route immediately
# after the page has been visited in the same context (see
# test_page_is_a_pooled_visitor_session). A route added here still has to
# prove the session; it just proves it one navigation later.
ROUTES_WITHOUT_GLOBAL_BASE = frozenset({"/apps/cards/"})

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

ROUTES = {route: (slug, title) for route, slug, title in PAGES}

WRITER_ROUTE = "/apps/writer/"
FIGRECIPE_ROUTE = "/apps/figrecipe/"

# Images this CI checkout CANNOT contain, named one by one.
#
# Django serves MEDIA_URL from MEDIA_ROOT = base_dir/'media'
# (config/settings/settings_static.py), which is a RUNTIME VOLUME:
# .gitignore excludes `media/` wholesale and `git ls-files media/` returns
# nothing. So the landing hero's thumbnail 404s on a runner and renders as
# the broken-image placeholder — which is exactly what 10-landing.png in
# run 32039805008 showed, and it is a fact about the runner, not about the
# product. Production mounts the volume and the hero plays.
#
# This is a DECLARATION, not a relaxation, and it is deliberately by exact
# src rather than by prefix: any OTHER broken image under /media/, on any
# page, still fails (test_page_has_no_undeclared_absent_media), and every
# broken image served from a path the repo DOES carry still fails outright.
# Adding a line here is a reviewable diff that has to say which file and
# why.
#
# The corresponding limitation on the artifact is stated once, loudly:
# 10-landing.png's hero panel is not representative. Do not put that
# screenshot in a talk without checking the hero against production.
DECLARED_ABSENT_MEDIA = {
    "/landing/": frozenset(
        {"/media/videos/scitex-automated-research-demo-thumbnail.png"}
    ),
}

FORCE_LIGHT = """
() => {
  document.documentElement.setAttribute('data-theme', 'light');
  document.documentElement.style.colorScheme = 'light';
}
"""


@pytest.fixture(scope="session")
def measured_content(pooled_visitor_page, content_report):
    """Measure a route's content ONCE, and let every check read that read.

    Session-scoped and cached BY ROUTE on purpose. The alternative —
    each assertion navigating for itself — costs a page load per check and,
    worse, means the "no loading placeholders" answer and the "no broken
    images" answer come from two different renders of the page. When one of
    them fails you then cannot tell whether the other was true at the same
    moment. One navigation, one ``page.evaluate``, one set of facts.

    Every measurement is written to the artifact's content-report.txt as it
    is taken, so the report covers pages whose assertions later fail too.
    """
    cache = {}
    browser_problems = BrowserProblemLog()
    browser_problems.attach(pooled_visitor_page)

    def _for(route):
        if route not in cache:
            slug, title = ROUTES[route]
            page = pooled_visitor_page
            # Reset immediately BEFORE the navigation, so what is collected
            # belongs to this route and not to the tail of the last one.
            browser_problems.reset()
            page.goto(route)
            wait_for_page_ready(
                page, hydration_signal=route not in ROUTES_WITHOUT_GLOBAL_BASE
            )
            page.evaluate(FORCE_LIGHT)
            signals = read_content_signals(page, PAGE_ELEMENT_SIGNALS.get(route))
            cache[route] = signals
            content_report(
                "%s\n%s"
                % (
                    describe_signals("%s (%s)" % (title, route), signals),
                    describe_browser_problems(browser_problems.drain()),
                )
            )
        return cache[route]

    return _for


@pytest.mark.parametrize("route,slug,title", PAGES, ids=[p[1] for p in PAGES])
class TestProductScreenshots:
    def test_page_is_served(self, pooled_visitor_page, route, slug, title):
        # Arrange
        page = pooled_visitor_page

        # Act
        response = page.goto(route)

        # Assert — a redirect is fine (sign-in walls, canonical paths);
        # a server error is not, and is what this is here to catch.
        status = response.status if response else 0
        assert status < 400, f"{title} ({route}) returned HTTP {status}"

    def test_page_is_a_pooled_visitor_session(
        self, pooled_visitor_page, route, slug, title
    ):
        """Re-checked PER PAGE, not once at setup.

        The warm-up proves the pool served a slot at the start of the run;
        this proves the session is STILL a pooled visitor on the page about
        to be photographed. A slot can lapse mid-run (the lease starts as a
        2-minute probation), and a lapsed session silently becomes the
        readonly-visitor fallback or anonymous — both of which render fine.

        For a route that does not render the marker
        (ROUTES_WITHOUT_GLOBAL_BASE) the page is still VISITED first, in
        this same browser context, and the session is then read on the
        warm-up route. Same session, same cookies, one navigation later.
        """
        # Arrange
        page = pooled_visitor_page
        carries_marker = route not in ROUTES_WITHOUT_GLOBAL_BASE
        page.goto(route)
        wait_for_page_ready(page, hydration_signal=carries_marker)
        if not carries_marker:
            page.goto(VISITOR_WARMUP_ROUTE)
            wait_for_page_ready(page)

        # Act
        role = page.evaluate(READ_SESSION_ROLE_JS)

        # Assert
        assert role == REQUIRED_ROLE, wrong_role_message(role, f"{title} ({route})")

    def test_page_renders_and_is_captured(
        self, pooled_visitor_page, screenshot, route, slug, title
    ):
        # Arrange
        page = pooled_visitor_page
        page.goto(route)
        # Wait for the product's own hydration signal, not `load` and not
        # `networkidle` — see tests/e2e/playwright/page_ready.py. These pages
        # hydrate after load, and photographing them too early captures empty
        # containers (measured 2026-08-16 — reading a page mid-hydration
        # produced four false "this is broken" reports in one session); but a
        # pooled-visitor session polls a heartbeat forever, so `networkidle`
        # is a condition it can never reach (measured 2026-08-16 in CI run
        # 31955719803: 30s timeout, 33 errors, nothing actually broken).
        wait_for_page_ready(
            page, hydration_signal=route not in ROUTES_WITHOUT_GLOBAL_BASE
        )
        page.evaluate(FORCE_LIGHT)

        # Act
        screenshot(page, slug)
        body_text = page.evaluate("() => (document.body.innerText || '').trim()")

        # Assert — a page that renders no visible text at all is broken,
        # and a blank PNG in the artifact would hide that. This is the
        # weakest of the content checks and is kept only as the floor
        # under them; what the page actually CONTAINS is asserted by
        # TestCapturedPageHasContent below.
        assert body_text, f"{title} ({route}) rendered no visible text"


@pytest.mark.parametrize("route,slug,title", PAGES, ids=[p[1] for p in PAGES])
class TestCapturedPageHasContent:
    """The checks that could have caught what run 32039805008 photographed.

    "The page painted" and "the page has content" are different questions,
    and the capture only ever asked the first one. These ask the second,
    generically, of every page in the set — so a screen that starts
    rendering its shell over an empty body fails the job that photographs
    it, which is the job's stated purpose.
    """

    def test_page_has_visible_content(self, measured_content, route, slug, title):
        # Arrange
        signals = measured_content(route)

        # Act
        problem = body_text_problem(signals, f"{title} ({route})")

        # Assert
        assert problem == "", problem

    def test_page_has_no_stuck_loading_placeholders(
        self, measured_content, route, slug, title
    ):
        # Arrange
        signals = measured_content(route)

        # Act
        problem = loading_marker_problem(signals, f"{title} ({route})")

        # Assert
        assert problem == "", problem

    def test_page_has_no_broken_images(self, measured_content, route, slug, title):
        # Arrange
        signals = measured_content(route)

        # Act
        problem = broken_image_problem(signals, f"{title} ({route})")

        # Assert
        assert problem == "", problem

    def test_page_has_no_undeclared_absent_media(
        self, measured_content, route, slug, title
    ):
        # Arrange
        signals = measured_content(route)

        # Act
        problem = undeclared_absent_media_problem(
            signals, DECLARED_ABSENT_MEDIA.get(route, frozenset()), f"{title} ({route})"
        )

        # Assert
        assert problem == "", problem


class TestWriterShowsAManuscript:
    """02-writer.png showed an editor with nothing in it.

    The file selector still read "Loading...", the word count still read
    "0", and the manuscript pane was empty — all three are the literal
    defaults shipped by ``index_partials/main_editor.html``. A screenshot
    of Writer that contains no writing is not a screenshot of Writer.
    """

    def test_file_selector_resolved(self, measured_content):
        # Arrange
        signals = measured_content(WRITER_ROUTE)

        # Act
        problem = stuck_placeholder_problem(
            signals, "file_selector", f"Writer ({WRITER_ROUTE})"
        )

        # Assert
        assert problem == "", problem

    def test_word_count_is_positive(self, measured_content):
        # Arrange
        signals = measured_content(WRITER_ROUTE)

        # Act
        problem = nonzero_count_problem(
            signals, "word_count", f"Writer ({WRITER_ROUTE})"
        )

        # Assert
        assert problem == "", problem


class TestFigRecipeShowsAGallery:
    """04-figrecipe.png was a header strip above an entirely blank body.

    ``#app-mount`` is where ``figrecipe_partial.html`` mounts the FigRecipe
    bundle. It painted; nothing mounted into it. Present-and-empty is the
    state that has to fail, because present-and-empty is what a page looks
    like when its front end never booted.
    """

    def test_mount_point_is_not_empty(self, measured_content):
        # Arrange
        signals = measured_content(FIGRECIPE_ROUTE)

        # Act
        problem = empty_container_problem(
            signals, "mount", f"FigRecipe ({FIGRECIPE_ROUTE})"
        )

        # Assert
        assert problem == "", problem
