#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cookie-consent (visitor-pool-full) page header touch-target tests.

Covers the 2026-07-08 iPhone field report: on the pre-consent
"Cookies Required for Visitor Slot Allocation" page the top-left logo
and top-right hamburger read as DEAD touch targets.

Contract under test (fix/cookie-consent-touch):
- the header logo on the consent page is a working link to /landing/
  (the default "/" bounces a pre-consent visitor straight back to the
  same page — a dead-looking tap);
- everywhere else the logo keeps its default "/" href;
- the mobile hamburger button renders together with its inline
  fail-safe script (data-inline-handler), so it works even when the
  Vite JS bundle fails to load;
- the mobile menu entries are real links (href present), not dead
  buttons.

Real Django test DB via django.test.TestCase — no mocks.
One assertion per test (STX-TQ007), AAA markers (STX-TQ002).
"""

from django.test import TestCase

BROWSER_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1"

CONSENT_URL = "/visitor-pool-full/"


class ConsentPageRendersTest(TestCase):
    """Anonymous browser without the consent cookie sees the consent page."""

    def test_consent_page_renders_cookies_required(self):
        # Arrange — no scitex_consent cookie on a fresh client
        # Act
        response = self.client.get(CONSENT_URL, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"Cookies Required for Visitor Slot Allocation" in response.content


class ConsentPageHeaderLogoTest(TestCase):
    """The header logo must never be a dead touch target."""

    def test_consent_page_logo_links_to_landing(self):
        # Arrange
        # Act
        response = self.client.get(CONSENT_URL, HTTP_USER_AGENT=BROWSER_UA)
        # Assert — pre-consent: "/" would redirect back to this very page
        assert b'href="/landing/" class="header-logo"' in response.content

    def test_landing_page_logo_keeps_default_home_href(self):
        # Arrange
        # Act
        response = self.client.get("/landing/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert — default header: logo points home
        assert b'href="/" class="header-logo"' in response.content


class ConsentPageHamburgerTest(TestCase):
    """The mobile hamburger renders WITH its inline fail-safe wiring."""

    def test_consent_page_renders_hamburger_button(self):
        # Arrange
        # Act
        response = self.client.get(CONSENT_URL, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b'id="mobile-hamburger-btn"' in response.content

    def test_consent_page_includes_inline_hamburger_failsafe(self):
        # Arrange
        # Act
        response = self.client.get(CONSENT_URL, HTTP_USER_AGENT=BROWSER_UA)
        # Assert — inline script marks the button so header.ts skips rewiring
        assert b"data-inline-handler" in response.content


class ConsentPageMobileMenuLinksTest(TestCase):
    """Mobile menu items are real links (href), not dead buttons."""

    def test_mobile_menu_contains_sign_in_link(self):
        # Arrange
        # Act
        response = self.client.get(CONSENT_URL, HTTP_USER_AGENT=BROWSER_UA)
        # Assert — anonymous menu offers a working Sign In link
        assert b'<a href="/auth/signin/" class="mobile-menu-item">' in response.content


# EOF
