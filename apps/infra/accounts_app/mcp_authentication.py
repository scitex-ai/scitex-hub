"""Authorize the host's complete umbrella MCP server, not a scoped leaf API."""

from dataclasses import dataclass

from channels.db import database_sync_to_async
from django.db import DatabaseError
from django.utils import timezone
from scitex_logging import getLogger

from .auth import resolve_api_key
from .models import APIKey

logger = getLogger(__name__)


@dataclass(frozen=True)
class MCPAuthorization:
    status: int
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.status == 200


async def authorize_host_mcp(scope) -> MCPAuthorization:
    """Require an active operator key, its MCP scope, and an available auth store.

    The endpoint mounts the umbrella's host-local tools. Campaign tokens and
    ordinary user keys do not authorize those capabilities. Leaf API admissions
    and standalone/local MCP servers use their own declared access contracts.
    """
    headers = dict(scope.get("headers", []))
    auth = headers.get(b"authorization", b"").decode("utf-8", errors="replace")
    if not auth.startswith("Bearer ") or not auth[7:].strip():
        return MCPAuthorization(401, "An active operator API key is required.")

    return await _authorize_key(auth[7:].strip())


@database_sync_to_async
def _authorize_key(raw_key: str) -> MCPAuthorization:
    """Complete database work with Channels' connection-lifecycle cleanup."""
    try:
        key, _reason = resolve_api_key(raw_key)
        if key is None:
            return MCPAuthorization(
                401, "The API key is invalid, expired, or inactive."
            )
        if not key.user.is_superuser or not (
            key.has_scope("mcp") or key.has_scope("*")
        ):
            return MCPAuthorization(
                403,
                "Host MCP requires a platform operator key with mcp or * scope. Use the app's scoped Web API for project operations.",
            )
        APIKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())
    except DatabaseError:
        logger.warning("Host MCP authentication store is unavailable", exc_info=True)
        return MCPAuthorization(
            503, "API authentication is temporarily unavailable; retry later."
        )
    return MCPAuthorization(200)
