#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/accounts_app/views/api_keys_views.py and MCP auth in config.asgi.

All tests use the real Django test DB (pytest-django `django_db` mark) and
real `User.objects.create_user` / `APIKey.create_key` calls — no mocks.
Each test asserts a single behaviour so the failing line in CI names
exactly which contract broke.
"""

import hashlib

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.infra.accounts_app.models import APIKey


@pytest.mark.django_db
class TestMCPAPIKeyValidationNoAuthHeader:
    """`_mcp_api_key_valid` behaviour when the request has no auth header."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_authorization_header(self):
        """No Authorization header at all -> False."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        scope = {"type": "http", "headers": []}
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is False


@pytest.mark.django_db
class TestMCPAPIKeyValidationInvalidKey:
    """`_mcp_api_key_valid` with a bearer token that isn't a real key."""

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_bearer_key(self):
        """Bearer token that doesn't match any APIKey row -> False."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer sk_invalid_key")],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is False


@pytest.mark.django_db
class TestMCPAPIKeyValidationFullAccessScope:
    """`_mcp_api_key_valid` with a real key carrying the wildcard '*' scope."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_key_with_wildcard_scope(self):
        """A real, active key with scopes=['*'] -> True."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser",
            password="testpass",  # pragma: allowlist secret
        )
        _, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-full", scopes=["*"]
        )
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_updates_last_used_at_after_successful_validation(self):
        """A successful validation stamps `last_used_at` on the row."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser_b",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-full-b", scopes=["*"]
        )
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        # Act
        await _mcp_api_key_valid(scope)
        await sync_to_async(api_key_obj.refresh_from_db)()
        # Assert
        assert api_key_obj.last_used_at is not None


@pytest.mark.django_db
class TestMCPAPIKeyValidationMcpScope:
    """`_mcp_api_key_valid` with a real key carrying scopes=['mcp']."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_key_with_mcp_scope(self):
        """scopes=['mcp'] is sufficient for the MCP endpoint."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser2",
            password="testpass",  # pragma: allowlist secret
        )
        _, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-mcp", scopes=["mcp"]
        )
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is True


@pytest.mark.django_db
class TestMCPAPIKeyValidationInsufficientScope:
    """`_mcp_api_key_valid` with a valid key whose scope doesn't grant MCP."""

    @pytest.mark.asyncio
    async def test_returns_false_for_valid_key_with_only_project_read_scope(
        self,
    ):
        """scopes=['project:read'] does not satisfy MCP -> False."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser3",
            password="testpass",  # pragma: allowlist secret
        )
        _, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-limited", scopes=["project:read"]
        )
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is False


@pytest.mark.django_db
class TestMCPAPIKeyValidationInactiveKey:
    """`_mcp_api_key_valid` with a valid-format but deactivated key."""

    @pytest.mark.asyncio
    async def test_returns_false_when_key_is_inactive(self):
        """A real key with is_active=False -> False even with the right scope."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser4",
            password="testpass",  # pragma: allowlist secret
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-inactive", scopes=["*"]
        )
        api_key_obj.is_active = False
        await sync_to_async(api_key_obj.save)()
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is False


@pytest.mark.django_db
class TestMCPAPIKeyValidationMalformedToken:
    """`_mcp_api_key_valid` with an empty bearer payload."""

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_bearer_token(self):
        """`Authorization: Bearer ` with no token -> False."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer ")],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is False


@pytest.mark.django_db
class TestMCPAPIKeyValidationWrongAuthScheme:
    """`_mcp_api_key_valid` with `Basic` instead of `Bearer`."""

    @pytest.mark.asyncio
    async def test_returns_false_for_basic_auth_scheme(self):
        """`Authorization: Basic ...` is rejected even with a real key value."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser5",
            password="testpass",  # pragma: allowlist secret
        )
        _, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-basic", scopes=["*"]
        )
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Basic {full_key}".encode())],
        }
        # Act
        result = await _mcp_api_key_valid(scope)
        # Assert
        assert result is False


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
