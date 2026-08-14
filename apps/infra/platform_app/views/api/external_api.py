"""
ExternalAPI proxy REST endpoint.

POST /api/platform/external/<api_name>/
    Body: {
        "method": "GET",          # HTTP method (required)
        "path":   "/works",       # Path appended to base_url (required)
        "params": {...},          # Query parameters (optional)
        "data":   {...}           # Request body for POST/PUT (optional)
    }

Looks up the API config from the registry (keyed by the calling app),
creates an ExternalAPIProxy, and forwards the request.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.infra.platform_app.services.external_api.proxy import (
    ExternalAPIProxy,
    MethodNotAllowedError,
    PathEscapesBaseURLError,
    RateLimitExceededError,
)
from apps.infra.platform_app.services.external_api.registry import (
    APINotFoundError,
    get_api,
)

logger = logging.getLogger(__name__)

# The app_name is resolved from the X-App-Name header or query param.
# This lets multiple user-apps share a single URL namespace.
_APP_NAME_HEADER = "HTTP_X_APP_NAME"
_APP_NAME_PARAM = "app_name"
_DEFAULT_APP_NAME = "platform"


def _resolve_app_name(request) -> str:
    """Extract app_name from header or query string, falling back to default."""
    return (
        request.META.get(_APP_NAME_HEADER)
        or request.GET.get(_APP_NAME_PARAM)
        or _DEFAULT_APP_NAME
    )


@login_required
@require_POST
def external_proxy(request, api_name: str) -> JsonResponse:
    """
    Forward a request to a registered external API.

    Path param:
        api_name — logical API identifier as registered in the registry.

    Request headers (optional):
        X-App-Name — owner app name used for registry lookup (default: "platform").

    Request body (JSON):
        method  str   HTTP verb, e.g. "GET" (required)
        path    str   URL path appended to base_url, e.g. "/works" (required)
        params  dict  Query string parameters (optional)
        data    dict  JSON body for POST/PUT (optional)

    Response (JSON):
        On success:  {"success": true,  "data": <upstream JSON>}
        On error:    {"success": false, "error": "<message>"}
    """
    # ── Parse request body ──────────────────────────────────────────────
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body"}, status=400
        )

    method = body.get("method", "").strip()
    path = body.get("path", "").strip()

    if not method:
        return JsonResponse(
            {"success": False, "error": "'method' is required"}, status=400
        )
    if not path:
        return JsonResponse(
            {"success": False, "error": "'path' is required"}, status=400
        )

    params = body.get("params") or None
    data = body.get("data") or None

    # ── Resolve app and config ───────────────────────────────────────────
    app_name = _resolve_app_name(request)

    try:
        config = get_api(app_name, api_name)
    except APINotFoundError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=404)

    # ── Build proxy and forward ──────────────────────────────────────────
    proxy = ExternalAPIProxy(app_name=app_name, api_config=config)
    user_id = request.user.id

    try:
        result = proxy.request(
            method=method,
            path=path,
            params=params,
            data=data,
            user_id=user_id,
        )
    except MethodNotAllowedError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=405)
    except PathEscapesBaseURLError as exc:
        # 400, not 502: the caller sent a bad path, the upstream never saw it.
        # Logged at WARNING because a rejected escape is a probe, not noise.
        logger.warning(
            "[ExternalAPI] rejected out-of-base path for '%s/%s' (user=%s): %s",
            app_name,
            api_name,
            user_id,
            exc,
        )
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    except RateLimitExceededError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=429)
    except Exception as exc:
        logger.error(
            "[ExternalAPI] Upstream error for '%s/%s': %s",
            app_name,
            api_name,
            exc,
        )
        return JsonResponse({"success": False, "error": str(exc)}, status=502)

    return JsonResponse({"success": True, "data": result})


# EOF
