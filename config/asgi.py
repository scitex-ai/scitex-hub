"""
ASGI config for SciTeX Cloud project.

HTTP routing:
  /mcp  → FastMCP (scitex tools), requires Bearer API key
  /*    → Django application

Exposes the ASGI callable as a module-level variable named ``application``.
"""

import hashlib
import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

settings_module = os.getenv("SCITEX_CLOUD_DJANGO_SETTINGS_MODULE") or "config.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
django.setup()

# Import routing after Django setup (must come after django.setup())
from apps.console_app import routing as code_routing  # noqa: E402
from apps.project_app import routing as project_routing  # noqa: E402
from apps.writer_app import routing as writer_routing  # noqa: E402

# Combine all WebSocket routes
websocket_urlpatterns = (
    writer_routing.websocket_urlpatterns
    + code_routing.websocket_urlpatterns
    + project_routing.websocket_urlpatterns
)

# Lazy-loaded FastMCP ASGI app — loads on first /mcp request to keep startup fast
_mcp_http_app = None


def _get_mcp_http_app():
    global _mcp_http_app
    if _mcp_http_app is None:
        from scitex.mcp_server import mcp as _scitex_mcp

        _mcp_http_app = _scitex_mcp.http_app()
    return _mcp_http_app


async def _send_json_error(send, status: int, message: str) -> None:
    body = f'{{"error": "{message}"}}'.encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _mcp_api_key_valid(scope) -> bool:
    """Return True if the request carries a valid APIKey with mcp or full-access scope."""
    headers = dict(scope.get("headers", []))
    auth = headers.get(b"authorization", b"").decode("utf-8", errors="replace")
    if not auth.startswith("Bearer "):
        return False
    raw_key = auth[7:].strip()
    if not raw_key:
        return False
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    try:
        from django.utils import timezone

        from apps.accounts_app.models import APIKey

        api_key = await APIKey.objects.aget(key_hash=key_hash, is_active=True)
        # Require mcp or full-access scope
        if not ("*" in api_key.scopes or "mcp" in api_key.scopes):
            return False
        # Update last_used_at (fire-and-forget; ignore errors)
        api_key.last_used_at = timezone.now()
        await api_key.asave(update_fields=["last_used_at"])
        return True
    except Exception:
        return False


_django_http_app = get_asgi_application()


async def _http_router(scope, receive, send):
    """Route /mcp → FastMCP (auth-protected), everything else → Django."""
    path = scope.get("path", "")
    if path == "/mcp" or path.startswith("/mcp/"):
        if not await _mcp_api_key_valid(scope):
            await _send_json_error(
                send,
                401,
                "Valid API key required. Use: Authorization: Bearer <key>",
            )
            return
        await _get_mcp_http_app()(scope, receive, send)
    else:
        await _django_http_app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": _http_router,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
