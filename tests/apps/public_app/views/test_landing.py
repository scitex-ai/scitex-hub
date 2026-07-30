#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/public_app/views/landing.py — the marketing landing
and its hero CTA area.

Card hub-landing-page-for-logged-out-visitors-20260727 (explicit-entry CTA):

Entering a visitor session must be a DELIBERATE, clearly-labeled choice. The
hero presents three options: an explicit "Enter as visitor" primary button
(target /enter/, a visitor-provisioning entry) plus "Sign up" and "Sign in" as
the alternatives. The rest of the marketing landing is unchanged (operator:
keep the existing landing).

The CTA target MOVED from /apps/home/ to /enter/ (card
hub-visitor-funnel-first-impression-20260730). Both provision a slot, but
/apps/home/ renders the Gitea repository browser — deliberately, per the
approved 2026-07-07 design — so a visitor's first screen was a file listing.
/enter/ provisions and then lands on the app launcher.

No mocks — real Django test DB + test client. One assertion per test
(STX-TQ007).
"""

from django.test import TestCase
from django.urls import reverse


class LandingHeroCtaTest(TestCase):
    """The marketing landing renders anonymously and offers the three
    explicit entry choices: Enter as visitor / Sign up / Sign in."""

    def test_landing_renders_for_anonymous(self):
        # Arrange: an anonymous visitor (default test client UA is non-browser)
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert resp.status_code == 200

    def test_hero_cta_is_enter_as_visitor(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — explicit, clearly-labeled visitor-entry button
        assert b"Enter as visitor" in resp.content

    def test_hero_cta_targets_visitor_provisioning_entry(self):
        # Arrange — the entry path, reversed so a route rename cannot rot this
        entry = reverse("public_app:visitor_enter").encode()
        # Act
        resp = self.client.get("/landing/")
        # Assert — target is a visitor-provisioning entry, now the dedicated
        # /enter/ route rather than /apps/home/. The INVARIANT this test names
        # is unchanged and still enforced; only the entry moved. /apps/home/
        # also provisioned, but rendered the Gitea repository browser, so the
        # first thing a visitor saw was dotfiles and "No commit message" x6.
        assert b'href="' + entry + b'"' in resp.content

    def test_hero_cta_no_longer_targets_repo_browser(self):
        # Arrange — paired with the positive assertion above on the same marker,
        # because a negative assertion alone would also pass if the CTA anchor
        # disappeared entirely.
        # Act
        resp = self.client.get("/landing/")
        # Assert — /apps/home/ keeps serving the repo browser by design
        # (approved 2026-07-07, repo_app/views/dispatch.py:13-17), so the hero
        # must not send a first-time visitor there.
        assert b'href="/apps/home/" class="hero-cta-button"' not in resp.content

    def test_hero_cta_note_explains_no_signup(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — subtext makes the "temporary, no sign-up" nature explicit
        assert b"No sign-up needed" in resp.content

    def test_landing_offers_sign_up(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — Sign up alternative points at the real auth URL
        assert b"/auth/signup/" in resp.content

    def test_landing_offers_sign_in(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — Sign in alternative points at the real auth URL
        assert b"/auth/login/" in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
