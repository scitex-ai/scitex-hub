#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_onsite_auth_bypass.py
"""Exploit-regression: on-site (X-SciTeX-OnSite) authentication bypass.

CONFIRMED VULNERABILITY (card sec-onsite-auth-header-impersonation)
-------------------------------------------------------------------
``OnSiteAuthMiddleware`` used to authenticate ANY request that carried a
bare ``X-SciTeX-OnSite: <username>`` header, provided the request "looked
internal". "Internal" was decided by::

    remote_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]

— the LEFTMOST X-Forwarded-For entry, which is exactly the value the
CLIENT writes (nginx *appends* the real peer via
``$proxy_add_x_forwarded_for``, so a forged entry stays first). So::

    curl -H 'X-Forwarded-For: 127.0.0.1' \
         -H 'X-SciTeX-OnSite: admin' https://scitex.ai/<any-endpoint>

authenticated an anonymous internet caller AS ``admin`` and set
``request._dont_enforce_csrf_checks = True``: unauthenticated account
takeover. The REMOTE_ADDR fallback was no better — behind the nginx
container every proxied request arrives with a 172.16/12 bridge address,
which the old trusted-prefix list accepted.

The fix makes possession of the shared HMAC secret the only trust signal
(``scitex_hub._mcp_tools.api.verify_onsite``, which also enforces a
replay window and uses a constant-time comparison).

These tests drive the real middleware with attacker-controlled META and
assert the dangerous sink — the user lookup that yields ``request.user``
— is never reached. The lookup collaborator is injected (a hand-rolled
recording fake), so no database is needed and "did attacker input reach
the sink?" is directly observable. On the unpatched middleware the fake
records the attacker's username and ``request.user`` becomes that user.
"""

import time

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from apps.infra.project_app.middleware import OnSiteAuthMiddleware
from scitex_hub._mcp_tools.api import (
    ONSITE_SIG_HEADER,
    ONSITE_TS_HEADER,
    ONSITE_USER_HEADER,
    sign_onsite,
    wsgi_meta_key,
)

pytestmark = pytest.mark.security

SECRET = "shared-onsite-secret-for-tests"
VICTIM = "admin"
ATTACKER_IP = "203.0.113.9"  # TEST-NET-3 — unmistakably public


class FakeUser:
    """Stand-in for an authenticated ``django.contrib.auth`` user."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, username):
        self.username = username


class RecordingUserLookup:
    """Hand-rolled user-lookup collaborator that records every call.

    Any recorded call means an attacker-supplied username reached the
    identity sink — i.e. the middleware believed the request.
    """

    def __init__(self):
        self.lookups = []

    def __call__(self, username):
        self.lookups.append(username)
        return FakeUser(username)


@pytest.fixture
def lookups():
    return RecordingUserLookup()


@pytest.fixture
def onsite_secret():
    with override_settings(ONSITE_AUTH_SECRET=SECRET):
        yield SECRET


@pytest.fixture
def no_onsite_secret():
    with override_settings(ONSITE_AUTH_SECRET=""):
        yield ""


@pytest.fixture
def middleware(lookups):
    mw = OnSiteAuthMiddleware(lambda request: "downstream-response")
    mw.user_lookup = lookups
    return mw


def anonymous_request(**meta):
    """An anonymous request carrying attacker-chosen META."""
    request = RequestFactory().get("/project/api/files/", **meta)
    request.user = AnonymousUser()
    return request


def forged_xff_request():
    """The published exploit: forged XFF + bare on-site username header."""
    return anonymous_request(
        REMOTE_ADDR=ATTACKER_IP,
        # nginx APPENDS the real peer, so the forged entry stays leftmost
        # — and leftmost is the element the vulnerable code read.
        HTTP_X_FORWARDED_FOR=f"127.0.0.1, {ATTACKER_IP}",
        HTTP_X_SCITEX_ONSITE=VICTIM,
    )


def signed_meta(username, secret, issued_at=None):
    ts = str(int(time.time() if issued_at is None else issued_at))
    return {
        wsgi_meta_key(ONSITE_USER_HEADER): username,
        wsgi_meta_key(ONSITE_TS_HEADER): ts,
        wsgi_meta_key(ONSITE_SIG_HEADER): sign_onsite(username, ts, secret),
    }


# ---------------------------------------------------------------------
# The exploit — forged X-Forwarded-For from the public internet
# ---------------------------------------------------------------------
def test_forged_xff_leaves_the_request_anonymous(middleware, onsite_secret):
    # Arrange
    request = forged_xff_request()
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: forged X-Forwarded-For + X-SciTeX-OnSite authenticated "
        f"an anonymous caller as {getattr(request.user, 'username', '?')!r}"
    )


def test_forged_xff_never_reaches_the_user_lookup(middleware, lookups, onsite_secret):
    # Arrange
    request = forged_xff_request()
    # Act
    middleware(request)
    # Assert
    assert lookups.lookups == [], (
        "AUTH BYPASS: attacker-controlled username reached the identity "
        f"sink: {lookups.lookups}"
    )


def test_forged_xff_does_not_disable_csrf_enforcement(middleware, onsite_secret):
    # Arrange
    request = forged_xff_request()
    # Act
    middleware(request)
    # Assert
    assert getattr(request, "_dont_enforce_csrf_checks", False) is False, (
        "AUTH BYPASS: forged on-site header disabled CSRF enforcement"
    )


# ---------------------------------------------------------------------
# Same exploit through the REMOTE_ADDR fallback
# ---------------------------------------------------------------------
def test_docker_bridge_remote_addr_leaves_the_request_anonymous(
    middleware, onsite_secret
):
    """Behind nginx every proxied request has a 172.16/12 REMOTE_ADDR."""
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="172.18.0.7", HTTP_X_SCITEX_ONSITE=VICTIM
    )
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: a docker-bridge REMOTE_ADDR was treated as proof of "
        "on-site origin"
    )


def test_loopback_remote_addr_leaves_the_request_anonymous(middleware, onsite_secret):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="127.0.0.1", HTTP_X_SCITEX_ONSITE=VICTIM
    )
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: an unsigned on-site header was accepted on loopback"
    )


# ---------------------------------------------------------------------
# Signature-level forgeries
# ---------------------------------------------------------------------
def test_username_swapped_under_a_valid_signature_is_rejected(
    middleware, onsite_secret
):
    """A signature legitimately issued for ``bob`` must not mint ``admin``."""
    # Arrange
    meta = signed_meta("bob", SECRET)
    meta[wsgi_meta_key(ONSITE_USER_HEADER)] = VICTIM
    request = anonymous_request(REMOTE_ADDR="127.0.0.1", **meta)
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: bob's signature authenticated the request as admin"
    )


def test_replayed_hour_old_signature_is_rejected(middleware, onsite_secret):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="127.0.0.1",
        **signed_meta(VICTIM, SECRET, issued_at=time.time() - 3600),
    )
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: a captured signature stayed valid outside the replay "
        "window"
    )


def test_signature_under_an_attacker_secret_is_rejected(middleware, onsite_secret):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="127.0.0.1", **signed_meta(VICTIM, "not-the-shared-secret")
    )
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: a signature made with the wrong secret was accepted"
    )


def test_unconfigured_secret_fails_closed(middleware, no_onsite_secret):
    """No secret configured means on-site auth is OFF, not 'trust everyone'."""
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="127.0.0.1", **signed_meta(VICTIM, SECRET)
    )
    # Act
    middleware(request)
    # Assert
    assert not request.user.is_authenticated, (
        "AUTH BYPASS: on-site auth authenticated a request with no "
        "ONSITE_AUTH_SECRET configured"
    )


# ---------------------------------------------------------------------
# The legitimate path must still work — otherwise everything above would
# pass simply because the feature had been deleted.
# ---------------------------------------------------------------------
def test_correctly_signed_request_authenticates_the_signed_user(
    middleware, onsite_secret
):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="172.18.0.7", **signed_meta(VICTIM, SECRET)
    )
    # Act
    middleware(request)
    # Assert
    assert request.user.username == VICTIM


def test_correctly_signed_request_marks_on_site_auth(middleware, onsite_secret):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="172.18.0.7", **signed_meta(VICTIM, SECRET)
    )
    # Act
    middleware(request)
    # Assert
    assert request._on_site_auth is True


def test_correctly_signed_request_is_exempt_from_csrf(middleware, onsite_secret):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="172.18.0.7", **signed_meta(VICTIM, SECRET)
    )
    # Act
    middleware(request)
    # Assert
    assert request._dont_enforce_csrf_checks is True


def test_already_authenticated_request_skips_the_on_site_path(
    middleware, lookups, onsite_secret
):
    # Arrange
    request = anonymous_request(
        REMOTE_ADDR="127.0.0.1", HTTP_X_SCITEX_ONSITE=VICTIM
    )
    request.user = FakeUser("session-user")
    # Act
    middleware(request)
    # Assert
    assert lookups.lookups == []
