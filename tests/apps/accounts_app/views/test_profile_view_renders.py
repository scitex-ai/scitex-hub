#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``/accounts/profile/`` renders for a signed-in user.

Regression (live audit 2026-09-14, compute-03): every signed-in GET returned
500 — ``AttributeError: 'User' object has no attribute 'ssh_public_keys'``.
The resource stats queried a relation that no longer exists; the real one is
``WorkspaceSSHKey.user`` (``related_name="workspace_ssh_keys"``), and the git
key is the single server-generated ``UserProfile.ssh_public_key``.

Real ``Client``, real ``User`` / ``WorkspaceSSHKey`` rows — no mocks.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.infra.accounts_app.models.ssh import WorkspaceSSHKey
from apps.infra.accounts_app.views.profile_views import gather_resource_statistics


def _signed_in_client(username: str) -> tuple[Client, User]:
    user = User.objects.create_user(username=username, password="pw-not-used-123")
    client = Client()
    client.force_login(user)
    return client, user


@pytest.mark.django_db
def test_signed_in_profile_page_returns_200():
    # Arrange
    client, _ = _signed_in_client("profile-200-user")
    # Act
    response = client.get(reverse("accounts_app:profile"))
    # Assert
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_stats_count_uploaded_workspace_ssh_keys():
    # Arrange
    _, user = _signed_in_client("profile-sshkey-user")
    WorkspaceSSHKey.objects.create(
        user=user,
        title="Laptop",
        public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIexample laptop",
        fingerprint="SHA256:example-fingerprint",
        key_type="ed25519",
    )
    # Act
    resources = gather_resource_statistics(user)
    # Assert
    assert resources["workspace_ssh_keys"] == 1
