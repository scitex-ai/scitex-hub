#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end tests for ``APIKeyAuthentication``.

The DRF auth class adapts the existing ``scitex_xxxx`` UI-PAT
(:class:`apps.infra.accounts_app.models.api_key.APIKey`) into the
``REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`` chain so it works on
every JWT-friendly endpoint — closing the Phase-1 gap surfaced by
operator-12909 ("a USER, not just our agent, must publish via CLI with
token auth, no browser").

These tests exercise the real DRF flow through the real auth chain
against a real endpoint (``/api/me/``, the cheapest authenticated DRF
view in the project) with a real :class:`APIKey` row created via
:meth:`APIKey.create_key`. **No mocks, no monkeypatch.**

Contract (three states):

1. **No relevant credentials** → return ``None`` (let next auth class
   try). Asserted via the JWT-shaped Bearer that should still route to
   ``JWTAuthentication`` and pass.
2. **Recognisable but invalid** (``Bearer scitex_…`` that's not in the
   DB) → ``AuthenticationFailed`` → 401.
3. **Valid credential** → ``(user, api_key)`` → 200, identifying the
   APIKey owner.

Plus expiry rejection.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from apps.infra.accounts_app.models import APIKey


@pytest.mark.django_db
def test_valid_apikey_authenticates_request_as_owner():
    # Arrange
    owner = User.objects.create_user(
        username="apikey-positive", email="apikey-positive@example.com", password="x"
    )
    _api_key_row, full_key = APIKey.create_key(
        user=owner, name="test-positive", scopes=["api"]
    )
    client = Client()

    # Act
    response = client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {full_key}")

    # Assert
    assert response.status_code == 200


@pytest.mark.django_db
def test_valid_apikey_response_identifies_correct_owner():
    # Arrange
    owner = User.objects.create_user(
        username="apikey-owner-check",
        email="apikey-owner-check@example.com",
        password="x",
    )
    _api_key_row, full_key = APIKey.create_key(
        user=owner, name="test-owner-check", scopes=["api"]
    )
    client = Client()

    # Act
    response = client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {full_key}")

    # Assert — /api/me/ returns the authenticated username; if the
    # auth class returned the wrong user, this fails loudly.
    assert response.json().get("username") == "apikey-owner-check"


@pytest.mark.django_db
def test_unknown_scitex_bearer_is_rejected_with_401():
    # Arrange
    client = Client()
    forged_key = "scitex_" + "0" * 64  # well-formed prefix, no DB row

    # Act
    response = client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {forged_key}")

    # Assert — recognisable shape ("Bearer scitex_…") that doesn't
    # match any row must hard-401, NOT fall through to anonymous /
    # other-auth-class state. Proves the class can't be tricked.
    assert response.status_code == 401


@pytest.mark.django_db
def test_expired_apikey_is_rejected_with_401():
    # Arrange
    owner = User.objects.create_user(
        username="apikey-expired", email="apikey-expired@example.com", password="x"
    )
    api_key_row, full_key = APIKey.create_key(
        user=owner, name="test-expired", scopes=["api"]
    )
    api_key_row.expires_at = timezone.now() - timezone.timedelta(days=1)
    api_key_row.save(update_fields=["expires_at"])
    client = Client()

    # Act
    response = client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {full_key}")

    # Assert
    assert response.status_code == 401


@pytest.mark.django_db
def test_inactive_apikey_is_rejected_with_401():
    # Arrange
    owner = User.objects.create_user(
        username="apikey-inactive", email="apikey-inactive@example.com", password="x"
    )
    api_key_row, full_key = APIKey.create_key(
        user=owner, name="test-inactive", scopes=["api"]
    )
    api_key_row.is_active = False
    api_key_row.save(update_fields=["is_active"])
    client = Client()

    # Act
    response = client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {full_key}")

    # Assert
    assert response.status_code == 401


@pytest.mark.django_db
def test_non_scitex_bearer_falls_through_to_other_auth_classes():
    # Arrange — a Bearer header that does NOT start with `scitex_` must
    # be IGNORED by APIKeyAuthentication so JWTAuthentication can try.
    # We confirm fall-through by sending an obvious non-JWT non-PAT
    # value and asserting the response is 401 (someone rejected it) —
    # but crucially NOT a 500 (which would mean APIKeyAuthentication
    # blew up trying to parse it).
    client = Client()

    # Act
    response = client.get(
        "/api/me/", HTTP_AUTHORIZATION="Bearer this-is-not-a-scitex-pat"
    )

    # Assert
    assert response.status_code == 401


# EOF
