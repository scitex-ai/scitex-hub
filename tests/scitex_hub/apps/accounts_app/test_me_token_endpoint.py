#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end security tests for ``/api/me/token/``.

Phase-1 PR-3 of operator-12909's token+CLI surface. The endpoint mints
a ``scitex_xxxx`` APIKey from a posted ``{username, password}`` so the
CLI can ``scitex-hub account token create`` without a browser.

Security review-hardening (lead msg db151d1 + dev msg 53b830f4 + dev
msg 089bd6 — locked into hub-card #34 spec). These tests pin each
invariant:

1. ``test_wrong_password_returns_401`` — wrong password → 401.
2. ``test_right_password_returns_token_and_least_priv_scope`` — right
   password → 201 with the token in body AND scope ⊆ {"publish"}.
3. ``test_minted_token_works_on_an_authenticated_endpoint`` — proves
   the returned token is the actual credential (round-trip).
4. ``test_constant_time_error_body_equality`` — wrong password and
   unknown username return BYTE-IDENTICAL bodies. This is the HARD
   anti-enumeration invariant per dev's 089bd6 refinement (the soft
   timing-median test lives in a manual benchmark script, not CI —
   see the runbook).
5. ``test_rate_limit_engagement_per_ip`` — 6th attempt within the
   per-IP window returns 429.
6. ``test_per_username_throttle_engages_across_ips`` — 6 attempts to
   the SAME username from DIFFERENT IPs within the per-username
   window returns 429 on the 6th. Defense-in-depth against
   credential-stuffing.
7. ``test_scope_allowlist_rejects_admin_scope`` — POST with
   ``scopes: ["api", "publish", "admin"]`` returns 400 NOT 201.
   Proves the server-side allowlist beats client trust.
8. ``test_logging_audit_excludes_password_and_token`` — captured log
   records do NOT contain the password substring NOR the minted token
   substring (only ``{username, ok}``). Turns the no-secret-logging
   grep-denylist into a permanent CI gate.

All tests use real Django ``Client`` + real DB (``@pytest.mark.django_db``)
+ real ``User.objects.create_user`` + real ``cache.clear()`` between
tests. NO mocks, NO monkeypatch.
"""

from __future__ import annotations

import logging
from typing import Tuple

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    """Reset the shared rate-limit cache between tests so per-IP and
    per-username buckets from one test don't bleed into the next."""
    cache.clear()
    yield
    cache.clear()


def _make_user(username: str = "alice", password: str = "pw-fixture") -> User:
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=password
    )


def _post_mint(
    client: Client,
    username: str,
    password: str,
    *,
    scopes=None,
    remote_addr: str = "10.0.0.1",
) -> Tuple[int, dict]:
    body = {"username": username, "password": password}
    if scopes is not None:
        body["scopes"] = scopes
    response = client.post(
        "/api/me/token/",
        data=body,
        content_type="application/json",
        REMOTE_ADDR=remote_addr,
    )
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, {}


# ---------------------------------------------------------------------
# (1) wrong password → 401
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_wrong_password_returns_401():
    # Arrange
    _make_user("wrongpw-user", "secret-password")

    # Act
    status_code, _body = _post_mint(Client(), "wrongpw-user", "WRONG")

    # Assert
    assert status_code == 401


# ---------------------------------------------------------------------
# (2) right password → 201 + token + scope ⊆ {"publish"}
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_right_password_returns_token_and_least_priv_scope():
    # Arrange
    _make_user("rightpw-user", "pw-fixture")

    # Act
    status_code, body = _post_mint(Client(), "rightpw-user", "pw-fixture")

    # Assert
    assert status_code == 201 and set(body["scopes"]) <= {"publish"}


# ---------------------------------------------------------------------
# (3) the minted token actually authenticates a downstream request
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_minted_token_works_on_an_authenticated_endpoint():
    # Arrange
    _make_user("roundtrip-user", "pw-fixture")
    _status, body = _post_mint(Client(), "roundtrip-user", "pw-fixture")
    minted = body["token"]

    # Act
    me_response = Client().get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {minted}")

    # Assert
    assert me_response.status_code == 200


# ---------------------------------------------------------------------
# (4) constant-time error body: wrong-pw == unknown-user (HARD invariant)
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_constant_time_error_body_equality():
    # Arrange
    _make_user("alice", "pw-fixture")

    # Act
    _wrong_status, body_wrong_pw = _post_mint(Client(), "alice", "WRONG")
    _unknown_status, body_unknown_user = _post_mint(
        Client(), "noway-such-user", "ANYTHING"
    )

    # Assert
    assert body_wrong_pw == body_unknown_user


# ---------------------------------------------------------------------
# (5) per-IP throttle engages
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_rate_limit_engagement_per_ip():
    # Arrange
    _make_user("rate-target", "pw-fixture")
    client = Client()

    # Act — burn the per-IP budget (5/minute per ENDPOINT_LIMITS) with
    # wrong-password attempts from the SAME IP, then probe one more.
    for _ in range(5):
        _post_mint(client, "rate-target", "WRONG", remote_addr="10.0.0.99")
    status_code, _ = _post_mint(client, "rate-target", "WRONG", remote_addr="10.0.0.99")

    # Assert
    assert status_code == 429


# ---------------------------------------------------------------------
# (6) per-username throttle engages across DIFFERENT IPs
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_per_username_throttle_engages_across_ips():
    # Arrange
    _make_user("victim", "pw-fixture")
    client = Client()

    # Act — 5 attempts spread across 5 distinct IPs to defeat the
    # per-IP throttle (each IP gets 1 hit; per-IP threshold is 5),
    # then a 6th from a 6th IP. The per-username counter (5 across all
    # IPs over 15 min) should fire on the 6th.
    for i in range(5):
        _post_mint(client, "victim", "WRONG", remote_addr=f"10.0.{i}.1")
    status_code, _ = _post_mint(client, "victim", "WRONG", remote_addr="10.0.99.1")

    # Assert
    assert status_code == 429


# ---------------------------------------------------------------------
# (7) scope-allowlist rejects admin scope at the auth layer
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_scope_allowlist_rejects_admin_scope():
    # Arrange
    _make_user("scope-test", "pw-fixture")

    # Act
    status_code, _body = _post_mint(
        Client(),
        "scope-test",
        "pw-fixture",
        scopes=["api", "publish", "admin"],
    )

    # Assert — server-side allowlist beats client trust. 400, not 201.
    assert status_code == 400


# ---------------------------------------------------------------------
# (8) logging audit — no password / no token in log records
# ---------------------------------------------------------------------


@pytest.mark.django_db
def test_logging_audit_excludes_password_and_token(caplog):
    # Arrange
    canary_password = "canary-pw-must-never-appear-9z3kq"  # pragma: allowlist secret
    _make_user("log-audit", canary_password)
    caplog.set_level(
        logging.DEBUG, logger="apps.infra.accounts_app.views.me_token_views"
    )

    # Act — one successful + one failed mint, covering the OK and
    # !OK arms of the log call.
    _status1, body = _post_mint(Client(), "log-audit", canary_password)
    minted_token = body["token"]
    _post_mint(Client(), "log-audit", "WRONG")

    # Assert
    captured = "\n".join(record.getMessage() for record in caplog.records)
    assert canary_password not in captured and minted_token not in captured


# EOF
