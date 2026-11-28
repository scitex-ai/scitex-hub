#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./tests/security/test_push_webhook_signature.py

"""The repository push webhook only runs for correctly signed Gitea requests.

Like the other Gitea -> Hub webhooks (see test_gitea_webhook_signature.py),
the push handler must refuse unsigned or wrongly signed bodies, and must fail
closed when no signing secret is configured.

The view is served here through a test URLconf so the requests go through the
real Django test client and middleware to the REAL view object exported by the
module (the decorator is part of that object, not re-applied by the test).
"""

from __future__ import annotations

import json
import os

import pytest
from django.test import Client, override_settings
from django.urls import path

from apps.infra.gitea_app.webhook_auth import (
    SECRET_NAME,
    SIGNATURE_HEADER,
    sign_gitea_body,
)
from apps.infra.project_app.views.repository.api.webhooks import webhook_push

pytestmark = [pytest.mark.security, pytest.mark.django_db]

SECRET = "test-push-webhook-secret-not-real"
URL = "/hooktest/no-such-user/no-such-project/api/webhook/push/"
BODY = json.dumps({"ref": "refs/heads/main", "commits": [{"id": "abc123"}]}).encode()

urlpatterns = [
    path(
        "hooktest/<str:username>/<slug:slug>/api/webhook/push/",
        webhook_push,
    ),
]


def _post(body: bytes, signature: str | None = None):
    headers = {}
    if signature is not None:
        headers[f"HTTP_{SIGNATURE_HEADER.upper().replace('-', '_')}"] = signature
    return Client().post(URL, data=body, content_type="application/json", **headers)


@pytest.fixture
def no_secret_in_environment():
    saved = os.environ.pop(SECRET_NAME, None)
    yield
    if saved is not None:
        os.environ[SECRET_NAME] = saved


@override_settings(ROOT_URLCONF=__name__, SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_unsigned_push_is_refused():
    # Arrange: no signature header at all
    body = BODY
    # Act
    response = _post(body)
    # Assert
    assert response.status_code == 403


@override_settings(ROOT_URLCONF=__name__, SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_wrongly_signed_push_is_refused():
    # Arrange
    bad = sign_gitea_body(BODY, "some-other-secret")
    # Act
    response = _post(BODY, bad)
    # Assert
    assert response.status_code == 403


@override_settings(ROOT_URLCONF=__name__, SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_signature_over_a_different_body_is_refused():
    # Arrange
    replayed = sign_gitea_body(b'{"ref": "refs/heads/other"}', SECRET)
    # Act
    response = _post(BODY, replayed)
    # Assert
    assert response.status_code == 403


@override_settings(ROOT_URLCONF=__name__, SCITEX_HUB_GITEA_WEBHOOK_SECRET=SECRET)
def test_correctly_signed_push_reaches_the_handler():
    # Arrange
    signed = sign_gitea_body(BODY, SECRET)
    # Act: the handler runs and looks the project up (none exists here)
    response = _post(BODY, signed)
    # Assert
    assert (response.status_code, json.loads(response.content)["error"]) == (
        404,
        "Project not found",
    )


@override_settings(ROOT_URLCONF=__name__, SCITEX_HUB_GITEA_WEBHOOK_SECRET="")
def test_unconfigured_secret_fails_closed(no_secret_in_environment):
    # Arrange: even a body "signed" with the empty secret must not pass
    signed = sign_gitea_body(BODY, "")
    # Act
    response = _post(BODY, signed)
    # Assert
    assert response.status_code == 503


# EOF
