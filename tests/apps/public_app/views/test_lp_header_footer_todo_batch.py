#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Landing page header/footer TODO batch.

Card hub-todo-lp-header-footer-batch-20260914 (operator TODO, active items):

1. Hero: no "Docs" / "License" buttons in the CTA row; Docs lives in the footer.
2. The language switcher lives in the footer, not the header.
3. Footer link lists carry no icons.
4. The dark-mode toggle is a single half-circle icon with an accessible label,
   and theme-switcher.ts no longer overwrites it with a sun/moon emoji.

Every negative ("not in X") assertion is paired with a positive control that
proves X was actually located, so a markup rename cannot make it pass
vacuously. Real Django test client, no mocks; one assertion per test.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

from django.test import TestCase

REPO_ROOT = Path(__file__).resolve().parents[4]
THEME_SWITCHER_TS = REPO_ROOT / "static/shared/ts/utils/theme-switcher.ts"


class _ElementSlicer(HTMLParser):
    """Collect the source span of every element matching (tag, attr predicate).

    Tracks nesting of the SAME tag so e.g. a <div> inside a <div> does not end
    the outer slice early.
    """

    def __init__(self, source, tag, predicate):
        super().__init__(convert_charrefs=False)
        self._source = source
        self._line_offsets = [0]
        for line in source.splitlines(keepends=True):
            self._line_offsets.append(self._line_offsets[-1] + len(line))
        self._tag = tag
        self._predicate = predicate
        self._depth = 0
        self._start = None
        self.slices = []

    def _pos(self):
        line, col = self.getpos()
        return self._line_offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag != self._tag:
            return
        if self._depth:
            self._depth += 1
        elif self._predicate(dict(attrs)):
            self._depth = 1
            self._start = self._pos()

    def handle_endtag(self, tag):
        if tag != self._tag or not self._depth:
            return
        self._depth -= 1
        if self._depth == 0:
            end = self._source.index(">", self._pos()) + 1
            self.slices.append(self._source[self._start : end])


def _slices(html, tag, predicate):
    parser = _ElementSlicer(html, tag, predicate)
    parser.feed(html)
    return parser.slices


def _first(html, tag, predicate):
    found = _slices(html, tag, predicate)
    return found[0] if found else ""


def _has_class(name):
    return lambda attrs: name in (attrs.get("class") or "").split()


class LandingHeaderFooterTodoBatchTest(TestCase):
    """Render the anonymous landing once per test and slice its regions."""

    def _page(self):
        return self.client.get("/landing/").content.decode("utf-8")

    def _hero(self):
        return _first(self._page(), "section", lambda a: a.get("id") == "home")

    def _header(self):
        return _first(self._page(), "header", _has_class("global-header"))

    def _footer(self):
        return _first(self._page(), "footer", _has_class("site-footer"))

    # --- 1. Hero CTA row --------------------------------------------------

    def test_hero_section_is_found_with_its_primary_cta(self):
        # Arrange — positive control for the two hero negatives below
        # Act
        hero = self._hero()
        # Assert
        assert 'class="hero-cta-button"' in hero

    def test_hero_has_no_docs_button(self):
        # Arrange
        hero = self._hero()
        # Act — any anchor in the hero pointing at a docs route
        docs_anchors = re.findall(r'<a\b[^>]*href="[^"]*docs[^"]*"', hero, re.I)
        # Assert
        assert docs_anchors == []

    def test_hero_has_no_license_button(self):
        # Arrange
        hero = self._hero()
        # Act — any anchor whose target or label mentions the license
        license_anchors = [
            a
            for a in re.findall(r"<a\b.*?</a>", hero, re.I | re.S)
            if "license" in a.lower()
        ]
        # Assert
        assert license_anchors == []

    def test_footer_contains_docs_link(self):
        # Arrange
        footer = self._footer()
        # Act
        match = re.search(r'<a href="/docs/">\s*Docs\s*</a>', footer)
        # Assert
        assert match is not None

    # --- 2. Language switcher placement ---------------------------------

    def test_header_element_is_found(self):
        # Arrange — positive control for "switcher not in header"
        # Act
        header = self._header()
        # Assert
        assert 'id="theme-toggle"' in header

    def test_language_switcher_is_inside_footer(self):
        # Arrange
        footer = self._footer()
        # Act
        found = 'id="lang-select"' in footer
        # Assert
        assert found

    def test_language_switcher_is_not_inside_header(self):
        # Arrange
        header = self._header()
        # Act
        found = 'id="lang-select"' in header
        # Assert
        assert not found

    def test_language_switcher_still_posts_to_set_language(self):
        # Arrange
        footer = self._footer()
        # Act
        match = re.search(r'<form action="/i18n/setlang/" method="post"', footer)
        # Assert
        assert match is not None

    # --- 3. Footer link lists carry no icons ----------------------------

    def test_footer_link_lists_are_found(self):
        # Arrange — positive control for the no-icon assertion
        # Act
        lists = _slices(self._footer(), "ul", _has_class("footer-links"))
        # Assert
        assert len(lists) == 3

    def test_footer_link_lists_have_no_icons(self):
        # Arrange
        lists = _slices(self._footer(), "ul", _has_class("footer-links"))
        # Act
        with_icons = [ul for ul in lists if re.search(r"<i\b|<svg\b", ul)]
        # Assert
        assert with_icons == []

    # --- 4. Theme toggle ------------------------------------------------

    def _theme_toggle(self):
        return _first(self._header(), "button", lambda a: a.get("id") == "theme-toggle")

    def test_theme_toggle_uses_half_circle_icon(self):
        # Arrange
        button = self._theme_toggle()
        # Act
        has_half_circle = "fa-circle-half-stroke" in button
        # Assert
        assert has_half_circle

    def test_theme_toggle_has_no_sun_or_moon_icon(self):
        # Arrange
        button = self._theme_toggle()
        # Act
        sun_moon = re.findall(r"fa-(?:sun|moon)|☀|\U0001F319", button)
        # Assert
        assert sun_moon == []

    def test_theme_toggle_has_aria_label(self):
        # Arrange
        button = self._theme_toggle()
        # Act
        match = re.search(r'aria-label="Switch to dark mode"', button)
        # Assert
        assert match is not None

    def test_theme_switcher_does_not_replace_the_icon_at_runtime(self):
        # Arrange — updateToggleButton used to set innerHTML to a sun/moon
        # emoji on every page load, hiding the server-rendered half-circle.
        source = THEME_SWITCHER_TS.read_text(encoding="utf-8")
        body = source.split("function updateToggleButton", 1)[1]
        body = body.split("\nfunction ", 1)[0]
        # Act
        rewrites_icon = "innerHTML" in body
        # Assert
        assert not rewrites_icon


# EOF
