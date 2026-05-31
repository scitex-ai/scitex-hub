#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/accounts_app/views/api_keys_views.py and MCP auth in config.asgi"""

import hashlib

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.infra.accounts_app.models import APIKey


@pytest.mark.django_db
class TestMCPAPIKeyValidation:
    """Test _mcp_api_key_valid function from config.asgi"""

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_no_auth_header(self):
        """_mcp_api_key_valid returns False when no Authorization header"""
        from config.asgi import _mcp_api_key_valid

        scope = {"type": "http", "headers": []}
        result = await _mcp_api_key_valid(scope)
        assert result is False

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_invalid_key(self):
        """_mcp_api_key_valid returns False when invalid key"""
        from config.asgi import _mcp_api_key_valid

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer sk_invalid_key")],
        }
        result = await _mcp_api_key_valid(scope)
        assert result is False

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_valid_key_full_access(self):
        """_mcp_api_key_valid returns True when valid key with * scope"""
        from config.asgi import _mcp_api_key_valid

        # Django sync ORM in async test → wrap with sync_to_async.
        user = await sync_to_async(User.objects.create_user)(
            username="testuser", password="testpass"
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-full", scopes=["*"]
        )

        # Test with valid key
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        result = await _mcp_api_key_valid(scope)
        assert result is True

        # Verify last_used_at was updated
        await sync_to_async(api_key_obj.refresh_from_db)()
        assert api_key_obj.last_used_at is not None

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_valid_key_mcp_scope(self):
        """_mcp_api_key_valid returns True when valid key with mcp scope"""
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser2", password="testpass"
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-mcp", scopes=["mcp"]
        )

        # Test with valid key
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        result = await _mcp_api_key_valid(scope)
        assert result is True

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_insufficient_scope(self):
        """_mcp_api_key_valid returns False when valid key with only project:read scope"""
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser3", password="testpass"
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-limited", scopes=["project:read"]
        )

        # Test with valid key but wrong scope
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        result = await _mcp_api_key_valid(scope)
        assert result is False

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_inactive_key(self):
        """_mcp_api_key_valid returns False when key is inactive"""
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser4", password="testpass"
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-inactive", scopes=["*"]
        )
        api_key_obj.is_active = False
        await sync_to_async(api_key_obj.save)()

        # Test with valid key that is inactive
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {full_key}".encode())],
        }
        result = await _mcp_api_key_valid(scope)
        assert result is False

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_malformed_bearer_token(self):
        """_mcp_api_key_valid returns False for malformed Bearer token"""
        from config.asgi import _mcp_api_key_valid

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer ")],  # Empty token
        }
        result = await _mcp_api_key_valid(scope)
        assert result is False

    @pytest.mark.asyncio
    async def test_mcp_api_key_valid_wrong_auth_type(self):
        """_mcp_api_key_valid returns False for non-Bearer auth"""
        from config.asgi import _mcp_api_key_valid

        user = await sync_to_async(User.objects.create_user)(
            username="testuser5", password="testpass"
        )
        api_key_obj, full_key = await sync_to_async(APIKey.create_key)(
            user=user, name="test-key-basic", scopes=["*"]
        )

        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Basic {full_key}".encode())],
        }
        result = await _mcp_api_key_valid(scope)
        assert result is False


@pytest.mark.django_db
class TestAPIKeysView:
    """Test API keys management view"""

    def test_api_keys_view_requires_login(self):
        """GET to the api-keys page requires authentication"""
        client = Client()
        response = client.get(reverse("accounts_app:api_keys"), follow=True)
        # Should redirect to login
        assert response.status_code == 200
        # Check we ended up at login page or redirected
        assert (
            any("login" in str(url).lower() for url in response.redirect_chain)
            or "login" in response.content.decode().lower()
        )

    def test_api_keys_view_logged_in_user(self):
        """GET to /settings/api-keys/ returns 200 for logged-in user"""
        client = Client()
        user = User.objects.create_user(
            username="testuser6",
            password="testpass123",  # pragma: allowlist secret
        )
        client.login(
            username="testuser6",
            password="testpass123",  # pragma: allowlist secret
        )

        response = client.get(reverse("accounts_app:api_keys"))
        assert response.status_code == 200

    def test_api_keys_view_context_data(self):
        """API keys view includes api_keys in context"""
        client = Client()
        user = User.objects.create_user(
            username="testuser7",
            password="testpass123",  # pragma: allowlist secret
        )
        client.login(
            username="testuser7",
            password="testpass123",  # pragma: allowlist secret
        )

        # Create some test API keys
        APIKey.create_key(user=user, name="key1", scopes=["*"])
        APIKey.create_key(user=user, name="key2", scopes=["mcp"])

        response = client.get(reverse("accounts_app:api_keys"))
        assert response.status_code == 200
        # Check context has api_keys
        assert "api_keys" in response.context


@pytest.mark.django_db
class TestAPIKeyModel:
    """Test APIKey model functionality"""

    def test_api_key_create_key(self):
        """APIKey.create_key() creates and returns key"""
        user = User.objects.create_user(username="testuser8", password="testpass")
        api_key_obj, full_key = APIKey.create_key(
            user=user, name="test-key", scopes=["*"]
        )

        assert api_key_obj.id is not None
        assert api_key_obj.user == user
        assert api_key_obj.name == "test-key"
        assert api_key_obj.scopes == ["*"]
        assert full_key.startswith("scitex_")
        assert api_key_obj.key_prefix == full_key[:14]

    def test_api_key_hash_verification(self):
        """APIKey stores and verifies key hash correctly"""
        user = User.objects.create_user(username="testuser9", password="testpass")
        api_key_obj, full_key = APIKey.create_key(
            user=user, name="test-key", scopes=["*"]
        )

        # Verify the key hash matches
        expected_hash = hashlib.sha256(full_key.encode()).hexdigest()
        assert api_key_obj.key_hash == expected_hash

    def test_api_key_verify_key_method(self):
        """APIKey.verify_key() correctly verifies keys"""
        user = User.objects.create_user(username="testuser10", password="testpass")
        api_key_obj, full_key = APIKey.create_key(
            user=user, name="test-key", scopes=["*"]
        )

        # Correct key should verify
        assert api_key_obj.verify_key(full_key) is True

        # Wrong key should not verify
        assert api_key_obj.verify_key("scitex_wrongkey") is False

    def test_api_key_has_scope(self):
        """APIKey.has_scope() checks scopes correctly"""
        user = User.objects.create_user(username="testuser11", password="testpass")

        # Test full access scope
        api_key_full, _ = APIKey.create_key(user=user, name="full-key", scopes=["*"])
        assert api_key_full.has_scope("mcp") is True
        assert api_key_full.has_scope("project:read") is True

        # Test specific scope
        api_key_mcp, _ = APIKey.create_key(user=user, name="mcp-key", scopes=["mcp"])
        assert api_key_mcp.has_scope("mcp") is True
        assert api_key_mcp.has_scope("project:read") is False

    def test_api_key_is_active_default(self):
        """APIKey.is_active defaults to True"""
        user = User.objects.create_user(username="testuser12", password="testpass")
        api_key_obj, _ = APIKey.create_key(user=user, name="test-key", scopes=["*"])

        assert api_key_obj.is_active is True
        assert api_key_obj.is_valid() is True


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
