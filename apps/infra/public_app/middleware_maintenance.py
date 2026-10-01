"""Generic maintenance admission for WSGI, Django ASGI, MCP and WebSockets."""

from __future__ import annotations

from html import escape

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpResponse, JsonResponse

from scitex_hub.maintenance import MaintenanceState, read_state

LIVE_PATH = "/livez/"
READY_PATH = "/maintenance-ready/"
HEALTH_PATH = "/healthz/"


def current_state():
    return read_state(getattr(settings, "SCITEX_HUB_MAINTENANCE_FILE", None))


def admission_response(path: str, accepts_json: bool, state: MaintenanceState):
    """Return an admission response without sessions, ORM, templates or leaf code."""
    if path == LIVE_PATH:
        response = JsonResponse({"status": "alive"})
    elif path == READY_PATH:
        response = JsonResponse(
            {
                "status": "maintenance" if state.enabled else "accepting_requests",
                "scope": "maintenance",
            },
            status=503 if state.enabled else 200,
        )
    elif not state.enabled or path == HEALTH_PATH:
        return None
    elif accepts_json or "/api/" in path or path == "/mcp" or path.startswith("/mcp/"):
        response = JsonResponse(
            {"error": "maintenance", "message": state.message}, status=503
        )
    else:
        response = HttpResponse(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>SciTeX maintenance</title><style>"
            "body{margin:0;background:#111827;color:#f9fafb;font:18px/1.6 system-ui;"
            "min-height:100vh;display:grid;place-items:center;padding:0 24px}"
            "main{max-width:36rem;min-width:0;overflow-wrap:anywhere}"
            "h1{line-height:1.2}p{color:#d1d5db}"
            "</style><main><h1>SciTeX maintenance</h1>"
            f"<p>{escape(state.message)}</p></main></html>",
            status=503,
        )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    if response.status_code == 503:
        response["Retry-After"] = str(state.retry_after)
    return response


class MaintenanceMiddleware:
    """Gate requests before session/auth/storage-dependent middleware executes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = admission_response(
            request.path_info,
            "application/json"
            in (
                request.headers.get("Accept", "")
                + request.headers.get("Content-Type", "")
            ),
            MaintenanceState() if request.path_info == LIVE_PATH else current_state(),
        )
        return response if response is not None else self.get_response(request)


class MaintenanceASGI:
    """Gate protocol admission, including MCP outside Django's middleware stack."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.application(scope, receive, send)
        state = (
            MaintenanceState()
            if scope["type"] == "http" and scope.get("path") == LIVE_PATH
            else await sync_to_async(current_state, thread_sensitive=False)()
        )
        if scope["type"] == "websocket":
            if state.enabled:
                await send(
                    {
                        "type": "websocket.close",
                        "code": 1013,
                        "reason": "Service temporarily unavailable",
                    }
                )
                return
        else:
            headers = dict(scope.get("headers", []))
            response = admission_response(
                scope.get("path", ""),
                b"application/json"
                in (headers.get(b"accept", b"") + headers.get(b"content-type", b"")),
                state,
            )
            if response is not None:
                await send(
                    {
                        "type": "http.response.start",
                        "status": response.status_code,
                        "headers": [
                            (key.lower().encode("ascii"), value.encode("latin-1"))
                            for key, value in response.items()
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b""
                        if scope.get("method") == "HEAD"
                        else response.content,
                    }
                )
                return
        await self.application(scope, receive, send)
