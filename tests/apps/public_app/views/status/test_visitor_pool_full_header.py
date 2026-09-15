#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visitor-pool routes are RETIRED — they now return 410 Gone.

Pre-retirement (2026-07-08 iPhone field report) these tests covered the
"visitor-pool-full / cookies required" consent page: a real page with a header,
a mobile hamburger (with an inline fail-safe script), and mobile-menu links.

2026-09-10 the visitor sandbox was retired (signup-first): the visitor pool is
no longer allocated, and the old routes (/visitor-pool-full/, /visitor-expired/,
/visitor-restart/) now return a 410 (Not Modified → Gone) plain-text notice that
tells the user to sign up or sign in. There is no consent page, no header, no
hamburger to touch-target-test anymore.

This file is kept as the guard that the retired routes fail *loudly* (410, not a
silent 200 of a stale consent page, and not a bare 404) and point the user at
signup. The original header-touch-target coverage is obsolete — there is no
header on a 410 response.

Real Django test client — no mocks.
One assertion per test (STX-TQ007), AAA markers (STX-TQ002).
"""

from django.test import Client, SimpleTestCase

BROWSER_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1"

# Every retired visitor route shares the same 410 contract.
RETIRED_VISITOR_ROUTES = (
    "/visitor-pool-full/",
    "/visitor-expired/",
    "/visitor-restart/",
)

RETIRED_NOTICE = b"The visitor sandbox was retired"


def _client() -> Client:
    return Client(HTTP_USER_AGENT=BROWSER_UA)


class RetiredVisitorRouteReturns410Test(SimpleTestCase):
    """Each retired visitor route answers 410 Gone (fail-loud, not 200/404)."""

    def test_pool_full_route_is_gone(self):
        # Arrange
        client = _client()
        # Act
        response = client.get(RETIRED_VISITOR_ROUTES[0])
        # Assert — 410, not the old 200 consent page and not a silent 404
        assert response.status_code == 410

    def test_expired_route_is_gone(self):
        # Arrange
        client = _client()
        # Act
        response = client.get(RETIRED_VISITOR_ROUTES[1])
        # Assert
        assert response.status_code == 410

    def test_restart_route_is_gone(self):
        # Arrange
        client = _client()
        # Act
        response = client.get(RETIRED_VISITOR_ROUTES[2])
        # Assert
        assert response.status_code == 410


class RetiredVisitorRoutePointsAtSignupTest(SimpleTestCase):
    """The 410 body tells the user what to do instead (sign up / sign in)."""

    def test_pool_full_body_names_retirement(self):
        # Arrange
        client = _client()
        # Act
        response = client.get(RETIRED_VISITOR_ROUTES[0])
        # Assert — honest cause text, not a stale cookie-consent page
        assert RETIRED_NOTICE in response.content

    def test_pool_full_body_offers_sign_in(self):
        # Arrange
        client = _client()
        # Act
        response = client.get(RETIRED_VISITOR_ROUTES[0])
        # Assert — the path forward is sign in / sign up
        assert b"sign in" in response.content

    def test_pool_full_is_not_the_old_consent_page(self):
        # Arrange
        client = _client()
        # Act
        response = client.get(RETIRED_VISITOR_ROUTES[0])
        # Assert — the retired consent chrome must be gone (anti-vacuity guard)
        assert b"mobile-hamburger-btn" not in response.content
