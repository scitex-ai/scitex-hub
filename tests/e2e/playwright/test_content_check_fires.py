#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The positive control: prove the content checks can FAIL.

WHY THIS EXISTS. A gate nobody has watched fail is not a gate. The
screenshot job spent its whole life green while photographing a blank
FigRecipe, a Writer stuck on "Loading..." and a landing hero rendered as
a broken-image placeholder (run 32039805008 on develop, 11 PNGs, all
assertions satisfied). Adding stricter assertions and re-running the same
green job proves nothing at all — the previous assertions were also
"passing".

So every judgement in ``content_check.py`` is exercised here TWICE:

  * against a fixture page built to have the exact defect, which must
    produce a failure message naming it, and
  * against a healthy fixture page, which must produce no message —
    otherwise the gate is merely a machine that always says no, and the
    capture would fail on every page regardless of what it photographed.

NO MOCKS, and none are needed. The defects are real: a real
``ThreadingHTTPServer`` serving a real directory over real HTTP, a real
Chromium loading real HTML, a real 404 for the broken image. The thing
under test is "what does a browser measure on a page like this", and a
mock of a browser cannot answer that — which is why the answer this suite
gives is worth something.

RUNS WHERE THE CAPTURE RUNS. It lives under ``tests/e2e/`` and so is
skipped by the headless gate (``tests/conftest.py``
``pytest_collection_modifyitems``) and collected by anything passing
``--browser``. ``.github/workflows/screenshots.yml`` names this file
alongside the capture on purpose: the run that photographs the product is
the run that re-proves its own gate still bites.
"""

from __future__ import annotations

import base64
import functools
import http.server
import threading

import pytest

from tests.e2e.playwright.content_check import (
    body_text_problem,
    broken_image_problem,
    empty_container_problem,
    loading_marker_problem,
    nonzero_count_problem,
    read_content_signals,
    stuck_placeholder_problem,
)

# A real, valid 1x1 PNG. Served over HTTP so the healthy fixture's image
# genuinely loads and reports a non-zero naturalWidth.
REAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8"
    "BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# Enough visible prose to clear MIN_BODY_TEXT_CHARS comfortably, so a test
# about images or mount points is never accidentally a test about text.
PROSE = (
    "SciTeX Hub workspace. Projects, Writer, Scholar, FigRecipe, Tools, "
    "App Store, Cards, Chat and Docs are all reachable from here, and "
    "this paragraph exists so the page has real content to measure."
)

BLANK_PAGE = "<body><span>hi</span></body>"

STUCK_PAGE = (
    "<body><p>%s</p>"
    '<div class="section-selector-wrapper">'
    '<span id="section-selector-text">Loading...</span>'
    "</div></body>" % PROSE
)

BROKEN_IMAGE_PAGE = (
    '<body><p>%s</p><img src="/definitely-not-here.png" '
    'alt="SciTeX Automated Research Demo" width="320" height="180" />'
    "</body>" % PROSE
)

EMPTY_MOUNT_PAGE = (
    "<body><p>%s</p>"
    '<div id="app-mount" class="figrecipe-workspace" '
    'style="width:800px;height:600px"></div></body>' % PROSE
)

ZERO_COUNT_PAGE = (
    '<body><p>%s</p><span id="current-word-count">0</span> words</body>' % PROSE
)

HEALTHY_PAGE = (
    "<body><p>%s</p>"
    '<img src="/real.png" alt="a real image" width="320" height="180" />'
    '<div id="app-mount" style="width:800px;height:600px">'
    '<canvas width="400" height="300"></canvas><p>Figure gallery</p>'
    "</div>"
    '<span id="section-selector-text">Introduction</span>'
    '<span id="current-word-count">1284</span> words'
    "</body>" % PROSE
)

WRITER_SELECTORS = {
    "file_selector": "#section-selector-text",
    "word_count": "#current-word-count",
}
FIGRECIPE_SELECTORS = {"mount": "#app-mount"}


@pytest.fixture
def serve(tmp_path):
    """A REAL local HTTP server over a real directory of real files."""
    (tmp_path / "real.png").write_bytes(REAL_PNG)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(tmp_path)
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]

    def _serve(name, html):
        (tmp_path / name).write_text(html, encoding="utf-8")
        return "%s/%s" % (base, name)

    yield _serve
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture
def measure(page, serve):
    """Load a fixture page in a real browser and measure it."""

    def _measure(name, html, selectors=None):
        page.goto(serve(name, html))
        page.wait_for_load_state("load")
        # The same short settle the capture uses, for anything that paints
        # a beat after load — including an image resolving to its error.
        page.wait_for_timeout(300)
        return read_content_signals(page, selectors)

    return _measure


# ---------------------------------------------------------------------------
# The defects must be caught
# ---------------------------------------------------------------------------


def test_blank_page_fails_the_body_text_floor(measure):
    # Arrange
    signals = measure("blank.html", BLANK_PAGE)
    # Act
    problem = body_text_problem(signals, "blank fixture")
    # Assert
    assert "below the" in problem, "a near-empty page passed the text floor"


def test_stuck_loading_placeholder_is_caught(measure):
    # Arrange
    signals = measure("stuck.html", STUCK_PAGE)
    # Act
    problem = loading_marker_problem(signals, "stuck fixture")
    # Assert
    assert "Loading..." in problem, "a visible 'Loading...' was not reported"


def test_named_stuck_selector_is_caught(measure):
    # Arrange
    signals = measure("stuck.html", STUCK_PAGE, WRITER_SELECTORS)
    # Act
    problem = stuck_placeholder_problem(signals, "file_selector", "stuck fixture")
    # Assert
    assert "shipped" in problem, "the file selector's default text passed"


def test_broken_image_is_caught(measure):
    # Arrange
    signals = measure("broken.html", BROKEN_IMAGE_PAGE)
    # Act
    problem = broken_image_problem(signals, "broken-image fixture")
    # Assert
    assert "definitely-not-here.png" in problem, "a 404 image passed"


def test_empty_mount_point_is_caught(measure):
    # Arrange
    signals = measure("empty.html", EMPTY_MOUNT_PAGE, FIGRECIPE_SELECTORS)
    # Act
    problem = empty_container_problem(signals, "mount", "empty-mount fixture")
    # Assert
    assert "EMPTY" in problem, "a mounted-but-empty container passed"


def test_zero_word_count_is_caught(measure):
    # Arrange
    signals = measure("zero.html", ZERO_COUNT_PAGE, WRITER_SELECTORS)
    # Act
    problem = nonzero_count_problem(signals, "word_count", "zero-count fixture")
    # Assert
    assert "no positive count" in problem, "a zero word count passed"


def test_absent_element_is_caught(measure):
    # Arrange
    signals = measure("blank.html", BLANK_PAGE, FIGRECIPE_SELECTORS)
    # Act
    problem = empty_container_problem(signals, "mount", "blank fixture")
    # Assert
    assert "not in the DOM" in problem, "a missing mount point passed"


# ---------------------------------------------------------------------------
# ...and a healthy page must pass, or the gate is just a machine saying no
# ---------------------------------------------------------------------------


@pytest.fixture
def healthy(measure):
    """One measurement of the healthy fixture, shared by the checks below."""
    selectors = dict(WRITER_SELECTORS, **FIGRECIPE_SELECTORS)
    return measure("healthy.html", HEALTHY_PAGE, selectors)


def test_healthy_page_clears_the_body_text_floor(healthy):
    # Arrange
    where = "healthy fixture"
    # Act
    problem = body_text_problem(healthy, where)
    # Assert
    assert problem == "", problem


def test_healthy_page_has_no_loading_markers(healthy):
    # Arrange
    where = "healthy fixture"
    # Act
    problem = loading_marker_problem(healthy, where)
    # Assert
    assert problem == "", problem


def test_healthy_page_has_no_broken_images(healthy):
    # Arrange
    where = "healthy fixture"
    # Act
    problem = broken_image_problem(healthy, where)
    # Assert
    assert problem == "", problem


def test_healthy_page_has_a_filled_mount(healthy):
    # Arrange
    where = "healthy fixture"
    # Act
    problem = empty_container_problem(healthy, "mount", where)
    # Assert
    assert problem == "", problem


def test_healthy_page_has_a_resolved_selector(healthy):
    # Arrange
    where = "healthy fixture"
    # Act
    problem = stuck_placeholder_problem(healthy, "file_selector", where)
    # Assert
    assert problem == "", problem


def test_healthy_page_has_a_positive_word_count(healthy):
    # Arrange
    where = "healthy fixture"
    # Act
    problem = nonzero_count_problem(healthy, "word_count", where)
    # Assert
    assert problem == "", problem


# EOF
