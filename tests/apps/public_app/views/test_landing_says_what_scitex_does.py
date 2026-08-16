#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A first-time visitor must be told what SciTeX is and how to start.

WHAT HAPPENED. Operator, 2026-08-16, after taking screenshots for a grant
application: 「今は道具がバラバラで来訪者がいても何が何だかわからないと
思うので」 and 「人様に見せられるレベルではない」 — the tools are scattered
and a visitor would have no idea what any of it is.

He was right, and the cause was not missing work. ``landing.html`` loaded
SIXTEEN stylesheets — products, benefits, features, demos, testimonials,
pricing, faq, cta — while its ``{% block content %}`` rendered only the
announcement and the hero. Fetching https://scitex.ai/ returned 48 KB of
HTML containing exactly ONE content heading:

    SciTeX — Where Research Happens

followed by the footer. ``landing_demos.html`` (219 lines, its own CSS and
its own unit-tested TS entrypoint) and ``landing_commitment.html`` were
written, styled, tested — and never included. The ecosystem partial was
commented out with a note explaining where the ecosystem TABLE had moved,
which is a different thing from the module cards.

So the failure mode is: a section stops rendering and nothing notices,
because a template that includes nothing still returns HTTP 200 and still
passes every test that only checks the page loads.

WHY THIS TEST PARSES THE RENDERED TEXT. Its sibling
``test_landing_body_class.py`` records the lesson the hard way: a plain
``assert b"landing-page" in resp.content`` PASSED against a page that was
visibly broken, because the characters were present inside a leaked
comment. The same trap applies here — "Scholar" appears in this page's
CSS filenames and script paths whether or not a human can see the word.
So these tests extract the text a BROWSER would show, with <script> and
<style> content discarded, and assert against that.

WHAT IS DELIBERATELY NOT ASSERTED: any particular wording, ordering, or
styling. Pinning the marketing copy would make this a change-detector for
the next person editing a sentence. The property is that a visitor is told
which tools exist and is given a way in — not that the page says any
specific thing.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from django.test import TestCase

LANDING_URL = "/landing/"

# The modules the landing page introduces. These are product names, not copy:
# renaming one is a deliberate act that should update this list.
#
# "Visualizer" was the OLD name and was still in the dormant partial. The
# operator caught it on sight — 「コンソールとビジュアライザーは昔の名前ですね」
# — which is the general hazard with re-enabling long-commented-out markup:
# it stops being reviewed but does not stop being wrong. The registry
# (apps_app.AppsModule.label) is the authority; it lists FigRecipe, and it
# still lists Console, so only the one name was stale.
MODULE_NAMES = ("Scholar", "Writer", "Console", "FigRecipe")


class _VisibleText(HTMLParser):
    """Collect the text a browser would render, ignoring script/style bodies."""

    _SKIP = {"script", "style", "template", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            self._chunks.append(data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self._chunks).split())


def _visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return parser.text


class LandingSaysWhatSciTeXDoesTest(TestCase):
    """The landing page is the only thing most visitors will ever read."""

    def setUp(self):
        # Arrange — one real request, reused; no mocks.
        response = self.client.get(LANDING_URL)
        self.status = response.status_code
        self.text = _visible_text(response.content.decode("utf-8", "replace"))

    def test_landing_is_served(self):
        # Arrange
        expected = 200

        # Act
        actual = self.status

        # Assert
        assert actual == expected

    @pytest.mark.guards(
        defect=(
            "landing.html loaded 16 section stylesheets but its content block "
            "included only the announcement and hero, so the rendered page had "
            "one heading and never named a single module"
        )
    )
    def test_every_module_is_named_to_the_visitor(self):
        # Arrange
        names = MODULE_NAMES

        # Act
        missing = [name for name in names if name not in self.text]

        # Assert
        assert missing == [], (
            f"the landing page never names {missing} — a visitor cannot learn "
            "these exist. Check the includes in landing.html."
        )

    @pytest.mark.guards(
        defect=(
            "with no call to action rendered, a visitor who wanted to use "
            "SciTeX had no path from the landing page to an account"
        )
    )
    def test_the_visitor_is_given_a_way_in(self):
        # Arrange
        response = self.client.get(LANDING_URL)
        html = response.content.decode("utf-8", "replace")

        # Act
        has_signup_path = "/auth/signup" in html

        # Assert
        assert has_signup_path, (
            "the landing page offers no sign-up link, so a convinced visitor "
            "has nowhere to go"
        )

    # A "page has more than N words" guard was drafted here and DELETED
    # before it shipped. Measuring the real broken page showed it rendered
    # 168 visible words already — all of it nav and footer chrome — so the
    # threshold I had picked (120) would have passed on the very page this
    # file exists to catch. It would have been a gate that cannot fail,
    # sitting in the same file that argues against them. Raising the bound
    # to clear today's content would only tune it to today's copy. The
    # module-name test above pins the property that actually matters.
