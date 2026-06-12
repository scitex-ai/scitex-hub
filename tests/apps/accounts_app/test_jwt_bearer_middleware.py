#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end tests for ``JWTBearerToSessionMiddleware``.

The middleware lets plain Django views (``@require_http_methods``) accept a
SimpleJWT access token in the ``Authorization: Bearer …`` header without
the views themselves switching to DRF (``@api_view + IsAuthenticated``).
This file exercises that contract through the **real** middleware stack
and a **real** project-scoped endpoint
(``apps.infra.project_app.views.repository.api.git_status.api_git_status``)
— no mocks, no monkeypatch, no patched internals.

Two contracts, both required by the publish-flow design intent
(operator-12880 "ユーザは gitea を意識しないつくり") + the
review-hardening directive (catch only specific JWT errors, fail closed
on anything malformed):

1. POSITIVE — A valid JWT minted via
   ``RefreshToken.for_user(user).access_token`` reaches the project-scoped
   view AS that user; the owner-based read-access check passes and the
   view returns a non-"Permission denied" response.

2. NEGATIVE — A garbage / forged Bearer leaves the request anonymous,
   so the same view returns a "Permission denied" JSON body — proof
   that the middleware cannot be tricked into authenticating an
   attacker.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken

from apps.infra.project_app.models import Project


def _mint_access_token(user: User) -> str:
    """Real JWT issuance — the same call path the workspace console uses
    (``terminal_broker/shell.py:_make_short_lived_jwt``).
    """
    return str(RefreshToken.for_user(user).access_token)


@pytest.mark.django_db
def test_valid_bearer_jwt_authenticates_request_as_owner():
    """POSITIVE — valid JWT resolves to the owner; read-access granted."""
    # Arrange
    owner = User.objects.create_user(
        username="jwt-positive", email="jwt-positive@example.com", password="x"
    )
    project = Project.objects.create(
        name="jwt-positive-proj",
        slug="jwt-positive-proj",
        description="middleware positive-path probe",
        owner=owner,
        visibility="private",
    )
    token = _mint_access_token(owner)
    client = Client()

    # Act
    response = client.get(
        f"/{owner.username}/{project.slug}/api/git/status/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    # Assert — the owner-as-resolved-by-middleware passes the read-access
    # check; the view either succeeds or fails for an unrelated reason
    # (e.g. project dir not on disk in the test setup), but it MUST NOT
    # come back with the "Permission denied" payload that signals the
    # middleware never resolved the user.
    assert b"Permission denied" not in response.content


@pytest.mark.django_db
def test_garbage_bearer_leaves_request_anonymous_and_denies():
    """NEGATIVE — forged Bearer must NOT trick the middleware. Owner-scoped
    private project is denied because ``request.user`` stays anonymous."""
    # Arrange
    owner = User.objects.create_user(
        username="jwt-negative", email="jwt-negative@example.com", password="x"
    )
    project = Project.objects.create(
        name="jwt-negative-proj",
        slug="jwt-negative-proj",
        description="middleware negative-path probe",
        owner=owner,
        visibility="private",
    )
    client = Client()

    # Act
    response = client.get(
        f"/{owner.username}/{project.slug}/api/git/status/",
        HTTP_AUTHORIZATION="Bearer this.is.not-a-real-jwt",
    )

    # Assert — fail-closed: the malformed token produced an anonymous
    # request, the private owner-only project denied access, and the JSON
    # body says so verbatim.
    assert b"Permission denied" in response.content


# EOF
