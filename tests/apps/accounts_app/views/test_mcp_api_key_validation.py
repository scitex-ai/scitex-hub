"""Host MCP authentication with real API-key rows and the normal ASGI predicate."""

import pytest
import pytest_asyncio
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from apps.infra.accounts_app.models import APIKey
from django.db import connections


@pytest_asyncio.fixture(autouse=True)
async def close_authentication_thread_connections():
    yield
    await sync_to_async(connections.close_all)()


async def _persist_user(**values):
    """Real API-key identity rows without unrelated OS/Gitea provisioning."""
    values.pop("password", None)
    user = User(**values)
    user.set_unusable_password()
    await sync_to_async(User.objects.bulk_create)([user])
    return user


@pytest.mark.django_db(transaction=True)
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


@pytest.mark.django_db(transaction=True)
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


@pytest.mark.django_db(transaction=True)
class TestMCPAPIKeyValidationFullAccessScope:
    """`_mcp_api_key_valid` with a real key carrying the wildcard '*' scope."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_key_with_wildcard_scope(self):
        """A real, active key with scopes=['*'] -> True."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await _persist_user(
            username="testuser",
            is_superuser=True,
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

        user = await _persist_user(
            username="testuser_b",
            is_superuser=True,
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


@pytest.mark.django_db(transaction=True)
class TestMCPAPIKeyValidationMcpScope:
    """`_mcp_api_key_valid` with a real key carrying scopes=['mcp']."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_key_with_mcp_scope(self):
        """An active operator with mcp scope is admitted."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await _persist_user(
            username="testuser2",
            is_superuser=True,
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


@pytest.mark.django_db(transaction=True)
class TestMCPAPIKeyValidationInsufficientScope:
    """`_mcp_api_key_valid` with a valid key whose scope doesn't grant MCP."""

    @pytest.mark.asyncio
    async def test_returns_false_for_valid_key_with_only_project_read_scope(
        self,
    ):
        """scopes=['project:read'] does not satisfy MCP -> False."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await _persist_user(
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


@pytest.mark.django_db(transaction=True)
class TestMCPAPIKeyValidationInactiveKey:
    """`_mcp_api_key_valid` with a valid-format but deactivated key."""

    @pytest.mark.asyncio
    async def test_returns_false_when_key_is_inactive(self):
        """A real key with is_active=False -> False even with the right scope."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await _persist_user(
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


@pytest.mark.django_db(transaction=True)
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


@pytest.mark.django_db(transaction=True)
class TestMCPAPIKeyValidationWrongAuthScheme:
    """`_mcp_api_key_valid` with `Basic` instead of `Bearer`."""

    @pytest.mark.asyncio
    async def test_returns_false_for_basic_auth_scheme(self):
        """`Authorization: Basic ...` is rejected even with a real key value."""
        # Arrange
        from config.asgi import _mcp_api_key_valid

        user = await _persist_user(
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
