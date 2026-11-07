#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for API-key views, hashing, scope membership and key metadata.
Host MCP admission lives in test_mcp_api_key_validation.py.

All tests use the real Django test DB (pytest-django `django_db` mark) and
real `User.objects.create_user` / `APIKey.create_key` calls — no mocks.
Each test asserts a single behaviour so the failing line in CI names
exactly which contract broke.
"""

import hashlib

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.infra.accounts_app.models import APIKey


@pytest.mark.django_db
class TestAPIKeysViewAccess:
    """Test the api-keys management view's access-control behaviour."""

    def test_anonymous_get_redirects_to_login(self):
        """An anonymous GET ends at the login page (via redirect chain or body)."""
        # Arrange
        client = Client()
        # Act
        response = client.get(reverse("accounts_app:api_keys"), follow=True)
        # Assert
        assert (
            any("login" in str(url).lower() for url in response.redirect_chain)
            or "login" in response.content.decode().lower()
        )

    def test_anonymous_get_returns_200_after_redirect_chain(self):
        """The follow=True chain ends at a renderable page (200)."""
        # Arrange
        client = Client()
        # Act
        response = client.get(reverse("accounts_app:api_keys"), follow=True)
        # Assert
        assert response.status_code == 200

    def test_logged_in_user_gets_200(self):
        """A logged-in user can GET /settings/api-keys/ -> 200."""
        # Arrange
        client = Client()
        User.objects.create_user(
            username="testuser6",
            password="testpass123",  # pragma: allowlist secret
        )
        client.login(
            username="testuser6",
            password="testpass123",  # pragma: allowlist secret
        )
        # Act
        response = client.get(reverse("accounts_app:api_keys"))
        # Assert
        assert response.status_code == 200


@pytest.mark.django_db
class TestAPIKeysViewContext:
    """Test that the view ships `api_keys` in the template context."""

    def test_response_status_is_200_for_logged_in_user(self):
        """View returns 200 for the logged-in user with existing keys."""
        # Arrange
        client = Client()
        user = User.objects.create_user(
            username="testuser7",
            password="testpass123",  # pragma: allowlist secret
        )
        client.login(
            username="testuser7",
            password="testpass123",  # pragma: allowlist secret
        )
        APIKey.create_key(user=user, name="key1", scopes=["*"])
        APIKey.create_key(user=user, name="key2", scopes=["mcp"])
        # Act
        response = client.get(reverse("accounts_app:api_keys"))
        # Assert
        assert response.status_code == 200

    def test_context_includes_api_keys_key(self):
        """View context includes the `api_keys` key."""
        # Arrange
        client = Client()
        user = User.objects.create_user(
            username="testuser7b",
            password="testpass123",  # pragma: allowlist secret
        )
        client.login(
            username="testuser7b",
            password="testpass123",  # pragma: allowlist secret
        )
        APIKey.create_key(user=user, name="key1", scopes=["*"])
        APIKey.create_key(user=user, name="key2", scopes=["mcp"])
        # Act
        response = client.get(reverse("accounts_app:api_keys"))
        # Assert
        assert "api_keys" in response.context


@pytest.mark.django_db
class TestAPIKeyModelCreateKey:
    """`APIKey.create_key()` factory contract."""

    def test_create_key_persists_row_with_id(self):
        """After create, the returned row has a PK."""
        # Arrange
        user = User.objects.create_user(
            username="testuser8",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert api_key_obj.id is not None

    def test_create_key_associates_owner_user(self):
        """The new row's user FK points back at the caller-supplied user."""
        # Arrange
        user = User.objects.create_user(
            username="testuser8b",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert api_key_obj.user == user

    def test_create_key_stores_caller_supplied_name(self):
        """The row's `name` field matches what the caller passed."""
        # Arrange
        user = User.objects.create_user(
            username="testuser8c",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert api_key_obj.name == "test-key"

    def test_create_key_stores_caller_supplied_scopes(self):
        """The row's `scopes` field matches what the caller passed."""
        # Arrange
        user = User.objects.create_user(
            username="testuser8d",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert api_key_obj.scopes == ["*"]

    def test_create_key_returns_full_key_with_scitex_prefix(self):
        """The plaintext token starts with the ecosystem-wide `scitex_` prefix."""
        # Arrange
        user = User.objects.create_user(
            username="testuser8e",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        _, full_key = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert full_key.startswith("scitex_")

    def test_create_key_records_key_prefix_matching_full_key_head(self):
        """Row's `key_prefix` equals the leading N chars of the plaintext."""
        # Arrange
        user = User.objects.create_user(
            username="testuser8f",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, full_key = APIKey.create_key(
            user=user, name="test-key", scopes=["*"]
        )
        # Assert
        assert api_key_obj.key_prefix == full_key[: len(api_key_obj.key_prefix)]


@pytest.mark.django_db
class TestAPIKeyHashVerification:
    """The stored `key_hash` is the SHA-256 hex of the plaintext token."""

    def test_key_hash_equals_sha256_of_plaintext(self):
        """`row.key_hash == sha256(full_key).hexdigest()`."""
        # Arrange
        user = User.objects.create_user(
            username="testuser9",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, full_key = APIKey.create_key(
            user=user, name="test-key", scopes=["*"]
        )
        expected_hash = hashlib.sha256(full_key.encode()).hexdigest()
        # Assert
        assert api_key_obj.key_hash == expected_hash


@pytest.mark.django_db
class TestAPIKeyVerifyKey:
    """`APIKey.verify_key(plaintext)` accept/reject contract."""

    def test_verify_key_accepts_correct_plaintext(self):
        """The plaintext returned by `create_key` verifies."""
        # Arrange
        user = User.objects.create_user(
            username="testuser10",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_obj, full_key = APIKey.create_key(
            user=user, name="test-key", scopes=["*"]
        )
        # Act
        result = api_key_obj.verify_key(full_key)
        # Assert
        assert result is True

    def test_verify_key_rejects_wrong_plaintext(self):
        """A different bearer token does not verify."""
        # Arrange
        user = User.objects.create_user(
            username="testuser10b",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Act
        result = api_key_obj.verify_key("scitex_wrongkey")
        # Assert
        assert result is False


@pytest.mark.django_db
class TestAPIKeyHasScopeWildcard:
    """A key with scopes=['*'] satisfies any scope query."""

    def test_wildcard_scope_satisfies_mcp(self):
        """`has_scope('mcp')` is True for a `*` key."""
        # Arrange
        user = User.objects.create_user(
            username="testuser11",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_full, _ = APIKey.create_key(user=user, name="full-key", scopes=["*"])
        # Act
        result = api_key_full.has_scope("mcp")
        # Assert
        assert result is True

    def test_wildcard_scope_satisfies_project_read(self):
        """`has_scope('project:read')` is True for a `*` key."""
        # Arrange
        user = User.objects.create_user(
            username="testuser11b",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_full, _ = APIKey.create_key(user=user, name="full-key", scopes=["*"])
        # Act
        result = api_key_full.has_scope("project:read")
        # Assert
        assert result is True


@pytest.mark.django_db
class TestAPIKeyHasScopeSpecific:
    """A key with scopes=['mcp'] satisfies only that exact scope."""

    def test_mcp_scoped_key_satisfies_mcp_scope(self):
        """`has_scope('mcp')` is True for a `mcp` key."""
        # Arrange
        user = User.objects.create_user(
            username="testuser11c",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_mcp, _ = APIKey.create_key(user=user, name="mcp-key", scopes=["mcp"])
        # Act
        result = api_key_mcp.has_scope("mcp")
        # Assert
        assert result is True

    def test_mcp_scoped_key_does_not_satisfy_project_read_scope(self):
        """`has_scope('project:read')` is False for a `mcp` key."""
        # Arrange
        user = User.objects.create_user(
            username="testuser11d",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_mcp, _ = APIKey.create_key(user=user, name="mcp-key", scopes=["mcp"])
        # Act
        result = api_key_mcp.has_scope("project:read")
        # Assert
        assert result is False


@pytest.mark.django_db
class TestAPIKeyIsActiveDefault:
    """A freshly-created key is active and valid."""

    def test_is_active_defaults_to_true(self):
        """`row.is_active` is True after `create_key`."""
        # Arrange
        user = User.objects.create_user(
            username="testuser12",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert api_key_obj.is_active is True

    def test_is_valid_returns_true_for_fresh_active_key(self):
        """`row.is_valid()` is True for a fresh active key."""
        # Arrange
        user = User.objects.create_user(
            username="testuser12b",
            password="testpass",  # pragma: allowlist secret
        )
        # Act
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])
        # Assert
        assert api_key_obj.is_valid() is True


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
