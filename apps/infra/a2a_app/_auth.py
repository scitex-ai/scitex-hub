"""Bearer-token auth for A2A POST endpoints.

Validates ``Authorization: Bearer <token>`` by calling Gitea
``GET /api/v1/user`` with that bearer. Positive results are cached for
``CACHE_TTL_S`` seconds keyed by the raw token to keep latency bounded.

GET endpoints (discovery, AgentCards, fleet index) are public — this
decorator is applied only to POST handlers (JSON-RPC dispatch).

The accepted bearer is **the caller's own Gitea PAT**, scoped at
minimum ``read:user``. Each agent has a dedicated narrow-scope token
at ``~/.bash.d/secrets/010_scitex/orochi-gitea-agents/<id>.a2a-token``;
humans use their own PAT the same way.

See ``GITIGNORED/A2A_PROTOCOL_SUPPORT.md`` for the design rationale.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from functools import wraps
from typing import Callable

from django.http import JsonResponse

logger = logging.getLogger(__name__)

GITEA_URL = os.environ.get("SCITEX_HUB_GITEA_URL", "https://git.scitex.ai")
CACHE_TTL_S = 60.0
HTTP_TIMEOUT_S = 5.0

_CACHE: dict[str, tuple[dict, float]] = {}


def _validate_at_gitea(token: str) -> dict | None:
    """Return Gitea user dict for ``token``, or None if invalid/error."""
    now = time.time()
    cached = _CACHE.get(token)
    if cached and cached[1] > now:
        return cached[0]

    url = f"{GITEA_URL.rstrip('/')}/api/v1/user"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code != 401:
            logger.warning("Gitea validate HTTP %s: %s", e.code, e.reason)
        return None
    except (urllib.error.URLError, OSError, ValueError) as e:
        logger.warning("Gitea validate error: %s", e)
        return None

    if not isinstance(data, dict) or "login" not in data:
        return None

    _CACHE[token] = (data, now + CACHE_TTL_S)
    return data


def require_a2a_bearer(view: Callable) -> Callable:
    """Reject unauthenticated POSTs with 401; inject caller into request.

    Sets ``request.a2a_caller`` to the Gitea user dict on success so the
    wrapped view can log who called it.
    """

    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        auth = request.headers.get("Authorization", "")
        prefix = "Bearer "
        if not auth.startswith(prefix):
            resp = JsonResponse({"error": "missing bearer token"}, status=401)
            resp["WWW-Authenticate"] = 'Bearer realm="a2a.scitex.ai"'
            return resp
        token = auth[len(prefix) :].strip()
        if not token:
            return JsonResponse({"error": "empty bearer token"}, status=401)

        identity = _validate_at_gitea(token)
        if identity is None:
            return JsonResponse({"error": "invalid bearer token"}, status=401)

        request.a2a_caller = identity
        return view(request, *args, **kwargs)

    return _wrapped
