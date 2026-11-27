#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./tests/security/test_gitea_webhook_signature.py

"""Regression gate: Gitea → Hub webhooks must be signed.

Finding (API audit 2026-11-27)
------------------------------
``/api/gitea/webhook/sync/`` (org membership sync) and ``/api/apps/webhook/``
(PR merge → app approved, public and verified) are CSRF-exempt and checked
no signature. Any anonymous POST reached the handler, so anyone could add or
remove organisation members or approve a pending app.

How these tests work
--------------------
They resolve the REAL registered URL to the REAL view (so the URL-level
guard is exercised, not a re-wrapped copy) and send requests that are
unsigned, wrongly signed, and correctly signed. Signed requests use payloads
the handlers acknowledge without touching the database, so no DB is needed.
"""

from __future__ import annotations

import json
import os

import pytest
from django.test import RequestFactory, override_settings
from django.urls import resolve

from apps.infra.gitea_app.webhook_auth import (
    SECRET_NAME,
    SIGNATURE_HEADER,
    sign_gitea_body,
)

pytestmark = pytest.mark.security

SECRET = "test-webhook-secret-not-real"

# (url, payload the handler acknowledges without DB access, extra headers)
WEBHOOKS = [
    ("/api/gitea/webhook/sync/", {"action": "noop"}, {"X-Gitea-Event": "push"}),
    ("/api/apps/webhook/", {"action": "opened", "pull_request": {}}, {}),
]


def _post(url, body: bytes, headers: dict):
    meta = {f"HTTP_{k.upper().replace('-', '_')}": v for k, v in headers.items()}
    request = RequestFactory().post(
        url, data=body, content_type="application/json", **meta
    )
    match = resolve(url)
    return match.func(request, *match.args, **match.kwargs)


@pytest.fixture
def no_secret_in_environment():
    saved = os.environ.pop(SECRET_NAME, None)
    yield
    if saved is not None:
        os.environ[SECRET_NAME] = saved


@pytest.mark.parametrize("url,payload,extra", WEBHOOKS)
@override_settings(SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_unsigned_request_is_refused(url, payload, extra):
    # Arrange
    body = json.dumps(payload).encode()
    # Act
    response = _post(url, body, extra)
    # Assert
    assert response.status_code == 403


@pytest.mark.parametrize("url,payload,extra", WEBHOOKS)
@override_settings(SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_wrong_signature_is_refused(url, payload, extra):
    # Arrange
    body = json.dumps(payload).encode()
    bad = sign_gitea_body(body, "some-other-secret")
    # Act
    response = _post(url, body, {**extra, SIGNATURE_HEADER: bad})
    # Assert
    assert response.status_code == 403


@pytest.mark.parametrize("url,payload,extra", WEBHOOKS)
@override_settings(SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_signature_over_a_different_body_is_refused(url, payload, extra):
    # Arrange
    body = json.dumps(payload).encode()
    replayed = sign_gitea_body(b'{"action": "something-else"}', SECRET)
    # Act
    response = _post(url, body, {**extra, SIGNATURE_HEADER: replayed})
    # Assert
    assert response.status_code == 403


@pytest.mark.parametrize("url,payload,extra", WEBHOOKS)
@override_settings(SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_correctly_signed_request_reaches_the_handler(url, payload, extra):
    # Arrange
    body = json.dumps(payload).encode()
    signed = {**extra, SIGNATURE_HEADER: sign_gitea_body(body, SECRET)}
    # Act
    response = _post(url, body, signed)
    # Assert
    assert (response.status_code, json.loads(response.content)["ok"]) == (200, True)


@pytest.mark.parametrize("url,payload,extra", WEBHOOKS)
@override_settings(SCITEX_HUB_GITEA_WEBHOOK_SECRET="")
def test_unconfigured_secret_fails_closed(
    url, payload, extra, no_secret_in_environment
):
    # Arrange: even a request "signed" with the empty secret must not pass
    body = json.dumps(payload).encode()
    signed = {**extra, SIGNATURE_HEADER: sign_gitea_body(body, "")}
    # Act
    response = _post(url, body, signed)
    # Assert
    assert response.status_code == 503


# EOF
