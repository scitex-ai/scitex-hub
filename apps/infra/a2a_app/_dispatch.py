"""Tier 3 dispatch bridge: forward A2A JSON-RPC to the orochi hub.

When an agent has live dispatch enabled (currently controlled by the
``SCITEX_OROCHI_A2A_DISPATCHABLE_AGENTS`` env var, comma-separated
agent ids), POST /v1/agents/<name> bodies are forwarded to the hub
endpoint at ``${SCITEX_OROCHI_HUB_URL}/api/a2a/dispatch/<ws>/<name>/``
instead of being answered with the canned echo.

The hub blocks awaiting the agent's WebSocket reply, so this call may
take up to ~30s. On timeout the hub returns 504 — surface as a JSON-RPC
error to the caller.

For Tier 3 mock (mock-echo) the hub-side WS recipient is a tiny Python
script (see scitex-orochi/tier3-mock-echo); the same code path will
serve real Claude Code agents once their MCP grows an a2a-handler.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

HUB_URL = os.environ.get("SCITEX_OROCHI_HUB_URL", "https://scitex-orochi.com")
WORKSPACE = os.environ.get("SCITEX_OROCHI_A2A_WORKSPACE", "main")
HTTP_TIMEOUT_S = 35.0

_DISPATCHABLE = {
    a.strip()
    for a in os.environ.get("SCITEX_OROCHI_A2A_DISPATCHABLE_AGENTS", "").split(",")
    if a.strip()
}


def is_dispatchable(agent: str) -> bool:
    """Return True if ``agent`` should be forwarded to the live hub."""
    return agent in _DISPATCHABLE


def dispatch(agent: str, body: dict) -> tuple[int, dict]:
    """Forward ``body`` to the hub bridge for ``agent``.

    Returns ``(status_code, payload)``. ``payload`` is the parsed JSON
    response (the JSON-RPC reply on 200, an error envelope otherwise).

    Raises:
        ValueError: If ``agent`` is not in the dispatchable allowlist.
    """
    # ENFORCED HERE, not only at the call site. `agent` is interpolated into a
    # URL path below, so the allowlist is a security boundary — and until now
    # it lived entirely in the ONE caller (views.py: `if ... and
    # is_dispatchable(name)`). That is correct today and depends on every
    # future caller remembering, which is the failure mode a mechanical guard
    # exists to remove. Exact set membership, so no traversal can survive it.
    if not is_dispatchable(agent):
        raise ValueError(
            f"agent {agent!r} is not dispatchable; it is not in "
            f"SCITEX_OROCHI_A2A_DISPATCHABLE_AGENTS. Add it there, or check "
            f"is_dispatchable() before calling dispatch()."
        )

    url = f"{HUB_URL.rstrip('/')}/api/a2a/dispatch/{WORKSPACE}/{agent}/"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read())
        except Exception:  # noqa: BLE001
            payload = {"error": str(exc)}
        return exc.code, payload
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("a2a dispatch transport error to %s: %s", url, exc)
        return 502, {"error": f"hub unreachable: {exc}"}
