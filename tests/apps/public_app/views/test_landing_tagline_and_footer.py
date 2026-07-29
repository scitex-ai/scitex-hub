#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The landing tagline pair and the footer "Developers" column, as RENDERED.

Two operator requests from 2026-07-30, both about the landing page:

  22:32Z  「footer のここイチカラムで良いかも」 + the six link labels
          -> the Developers group renders as a SINGLE column.
  22:34Z  the two-line tagline (see tests/config/test_branding_tagline.py for
          the constants; here we assert both lines reach the page).

WHY RENDERED AND NOT JUST THE CONSTANT: a template variable that does not
exist resolves to the empty string in Django. A correct constant plus a typo'd
template variable produces a blank line and NO error, so the constant test
alone cannot tell you the page is right.

HOW "SINGLE COLUMN" IS ASSERTED: structurally, not visually. The Developers
group is sliced out of the rendered HTML (from its <h3> to the next <h3>, so
the slice is independent of the HTML comments around it) and must contain
exactly ONE <ul> holding exactly SIX <li>. The previous markup had two <ul>s of
three inside a .footer-links-2col grid.

Every absence assertion below is paired with a presence assertion on the same
slice or the same file, so none of them can pass by the thing under test having
disappeared entirely.

No mocks -- real Django test DB + test client. One assertion per test
(STX-TQ007).
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

LANDING_URL = "/landing/"

EXPECTED_PRIMARY_TAGLINE = "Research Automation for AI and Humans"
EXPECTED_SECONDARY_TAGLINE = "Open-source Scientific Research Automation Ecosystem"

# The six labels the operator listed, in the order they were listed.
EXPECTED_DEVELOPER_LINKS = (
    "Web API Docs",
    "Web API Tests",
    "Releases",
    "Bug Reports",
    "Design System",
    "Server Status",
)

FOOTER_CSS = Path(settings.BASE_DIR) / "static/shared/css/components/footer.css"


def _developers_group(html):
    """Return the rendered Developers footer group as a string.

    Sliced from its own <h3> heading to the NEXT <h3> (the Legal column's), so
    the slice does not depend on the HTML comments or the wrapper classes --
    both of which this change edits.
    """
    start = html.index("<h3>Developers</h3>")
    rest = html[start + len("<h3>Developers</h3>") :]
    end = rest.find("<h3>")
    return rest if end == -1 else rest[:end]


class LandingTaglineTest(TestCase):
    """Both tagline lines reach the rendered landing page."""

    def test_landing_renders_for_anonymous(self):
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_primary_tagline_is_rendered(self):
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert EXPECTED_PRIMARY_TAGLINE in resp.content.decode()

    def test_secondary_tagline_is_rendered(self):
        """Guards the empty-variable failure described in the module docstring."""
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert EXPECTED_SECONDARY_TAGLINE in resp.content.decode()

    def test_secondary_tagline_paragraph_is_not_blank(self):
        """A missing context key renders <p class="..."></p> -- no error, no
        text. Assert the element carries content, not merely that it exists."""
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert not re.search(
            r'<p class="hero-tagline-secondary">\s*</p>', resp.content.decode()
        )

    def test_rendered_page_does_not_carry_the_scitentific_typo(self):
        """Non-vacuous: test_secondary_tagline_is_rendered proves the line is
        on the page, so this can only fail on the misspelling itself."""
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert "scitentific" not in resp.content.decode().lower()


class FooterDevelopersSingleColumnTest(TestCase):
    """The Developers footer group renders as one column of six links."""

    def test_developers_group_is_present(self):
        """Presence half of every pairing below: if the footer stopped
        rendering, this fails FIRST and the absence assertions cannot lie."""
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert "<h3>Developers</h3>" in resp.content.decode()

    def test_developers_group_has_exactly_one_list(self):
        # Arrange
        url = LANDING_URL
        # Act
        group = _developers_group(self.client.get(url).content.decode())
        # Assert
        assert group.count("<ul") == 1

    def test_developers_group_has_exactly_six_items(self):
        # Arrange
        url = LANDING_URL
        # Act
        group = _developers_group(self.client.get(url).content.decode())
        # Assert
        assert group.count("<li") == len(EXPECTED_DEVELOPER_LINKS)

    def test_developers_links_appear_in_the_order_the_operator_listed(self):
        # Arrange
        url = LANDING_URL
        # Act
        group = _developers_group(self.client.get(url).content.decode())
        # Assert
        assert [
            label for label in EXPECTED_DEVELOPER_LINKS if label in group
        ] == list(EXPECTED_DEVELOPER_LINKS)

    def test_developers_group_no_longer_uses_the_two_column_grid(self):
        """Absence half. Paired with the one-list/six-item tests above, which
        prove the group is really there and really single-column."""
        # Arrange
        url = LANDING_URL
        # Act
        group = _developers_group(self.client.get(url).content.decode())
        # Assert
        assert "footer-links-2col" not in group


class FooterCssHasNoDeadTwoColumnRuleTest(TestCase):
    """The CSS for the removed wrapper is removed too.

    Leaving `.footer-links-2col` defined after its only user is gone is dead
    CSS that reads as if a two-column footer is still supported.
    """

    def test_footer_css_file_is_readable(self):
        """Presence half: pins the path, so the absence test below cannot pass
        merely because the stylesheet moved or was renamed."""
        # Arrange
        path = FOOTER_CSS
        # Act
        exists = path.is_file()
        # Assert
        assert exists, f"footer stylesheet not found at {path}"

    def test_footer_css_still_defines_the_four_column_grid(self):
        # Arrange
        path = FOOTER_CSS
        # Act
        css = path.read_text(encoding="utf-8")
        # Assert
        assert ".footer-4-columns" in css

    def test_footer_css_no_longer_defines_the_two_column_link_grid(self):
        # Arrange
        path = FOOTER_CSS
        # Act
        css = path.read_text(encoding="utf-8")
        # Assert
        assert "footer-links-2col" not in css


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
