"""
ASGI config for SciTeX Hub project.

HTTP routing:
  /mcp  → FastMCP (scitex tools), requires Bearer API key
  /*    → Django application

Exposes the ASGI callable as a module-level variable named ``application``.
"""

import asyncio
import logging
import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

settings_module = os.getenv("SCITEX_HUB_DJANGO_SETTINGS_MODULE") or "config.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
django.setup()

# Import routing after Django setup (must come after django.setup())
from apps.workspace.console_app import routing as code_routing  # noqa: E402
from apps.infra.llm_app import routing as llm_routing  # noqa: E402
from apps.infra.project_app import routing as project_routing  # noqa: E402
from apps.workspace.writer_app import routing as writer_routing  # noqa: E402

logger = logging.getLogger("config.asgi")

# Combine all WebSocket routes
websocket_urlpatterns = (
    writer_routing.websocket_urlpatterns
    + code_routing.websocket_urlpatterns
    + project_routing.websocket_urlpatterns
    + llm_routing.websocket_urlpatterns
)

# ---------------------------------------------------------------------------
# FastMCP ASGI app with lifespan management
#
# FastMCP's http_app() returns a Starlette app whose lifespan context manager
# initialises the StreamableHTTPSessionManager task group.  When the app is
# served directly by uvicorn, uvicorn sends ASGI lifespan events that trigger
# this.  Inside Django Channels' ProtocolTypeRouter, however, no lifespan
# events are forwarded — so we must manage it ourselves.
#
# Strategy: intercept the ASGI "lifespan" protocol type and forward
# startup / shutdown events to the MCP Starlette app so its session manager
# task group gets created before the first HTTP request arrives.
# ---------------------------------------------------------------------------
_mcp_http_app = None
_mcp_lifespan_started = asyncio.Event()
_mcp_lifespan_task = None


def _create_mcp_http_app():
    """Create the FastMCP Starlette app (call once)."""
    global _mcp_http_app
    if _mcp_http_app is None:
        from scitex.mcp_server import mcp as _scitex_mcp

        _mcp_http_app = _scitex_mcp.http_app(path="/mcp")
    return _mcp_http_app


async def _run_mcp_lifespan():
    """Enter the MCP Starlette app's lifespan and keep it alive.

    The lifespan context manager (from FastMCP's create_streamable_http_app)
    calls ``session_manager.run()`` which creates the anyio task group that
    StreamableHTTPSessionManager needs to handle requests.

    This coroutine enters that context manager, signals readiness via the
    ``_mcp_lifespan_started`` event, then blocks until cancelled (server
    shutdown).
    """
    mcp_app = _create_mcp_http_app()
    lifespan_cm = mcp_app.router.lifespan_context

    async with lifespan_cm(mcp_app):
        logger.info("MCP lifespan started — session manager task group ready")
        _mcp_lifespan_started.set()
        # Block until cancelled (process/server shutdown)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("MCP lifespan shutting down")


async def _ensure_mcp_lifespan():
    """Start the MCP lifespan background task if not already running."""
    global _mcp_lifespan_task
    if _mcp_lifespan_task is None:
        _mcp_lifespan_task = asyncio.ensure_future(_run_mcp_lifespan())
    await _mcp_lifespan_started.wait()


def _get_mcp_http_app():
    """Return the MCP app (must be called after _ensure_mcp_lifespan)."""
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
    """Compatibility predicate for the host MCP authorization decision."""
    from apps.infra.accounts_app.mcp_authentication import authorize_host_mcp

    return (await authorize_host_mcp(scope)).allowed


_django_http_app = get_asgi_application()


async def _http_router(scope, receive, send):
    """Route /mcp -> FastMCP (auth-protected), everything else -> Django."""
    path = scope.get("path", "")
    if path == "/mcp" or path.startswith("/mcp/"):
        from apps.infra.accounts_app.mcp_authentication import authorize_host_mcp

        authorization = await authorize_host_mcp(scope)
        if not authorization.allowed:
            await _send_json_error(send, authorization.status, authorization.message)
            return
        # Ensure the MCP lifespan (session manager task group) is running
        # before forwarding the first request.
        await _ensure_mcp_lifespan()
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
