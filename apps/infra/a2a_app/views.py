"""Django views for the A2A protocol surface at ``a2a.scitex.ai``."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from apps.infra.a2a_app import _card
from apps.infra.a2a_app._auth import require_a2a_bearer
from apps.infra.a2a_app import _dispatch
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

_TASKS: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _base_url(request) -> str:
    return request.build_absolute_uri("/").rstrip("/")


def _canned_reply(agent: str, user_text: str, base_url: str) -> str:
    card = _card.load_card(agent, base_url=base_url)
    if not card:
        return f"[unknown agent: {agent}]"
    role = (card.get("x-orochi") or {}).get("role_class", "agent")
    return (
        f"[{agent} | role={role}] received: {user_text!r}. "
        "Experimental A2A echo on a2a.scitex.ai (NAS, scitex-hub Django). "
        "Live runtime bridge to the orochi hub on mba is not yet wired."
    )


# ----------------------------------------
# GET handlers
# ----------------------------------------


@require_GET
def fleet_well_known(request):
    """GET /.well-known/agent.json — fleet-level AgentCard."""
    return JsonResponse(_card.fleet_card(_base_url(request)))


@require_GET
def agents_index(request):
    """GET /v1/agents/ — fleet roster."""
    return JsonResponse(_card.fleet_index(_base_url(request)))


@require_GET
def agent_well_known(request, name: str):
    """GET /v1/agents/<name>/.well-known/agent.json — per-agent card."""
    card = _card.load_card(name, base_url=_base_url(request))
    if card is None:
        return JsonResponse({"error": f"unknown agent: {name}"}, status=404)
    return JsonResponse(card)


# ----------------------------------------
# POST — JSON-RPC dispatch
# ----------------------------------------


def _handle_tasks_send(agent: str, params: dict, base_url: str) -> dict:
    task_id = params.get("id") or f"task-{uuid.uuid4().hex[:12]}"
    msg = params.get("message", {}) or {}
    parts = msg.get("parts", []) or []
    user_text = next(
        (p.get("text", "") for p in parts if p.get("type") == "text"),
        "",
    )

    reply = _canned_reply(agent, user_text, base_url)

    task = {
        "id": task_id,
        "sessionId": params.get("sessionId"),
        "status": {
            "state": "completed",
            "message": None,
            "timestamp": _now(),
        },
        "history": [
            msg,
            {
                "role": "agent",
                "parts": [{"type": "text", "text": reply}],
            },
        ],
        "artifacts": [],
        "metadata": {
            "x-orochi": {
                "agent": agent,
                "runtime": "experimental-echo",
                "served_by": "a2a.scitex.ai",
                "generated_at": _now(),
            }
        },
    }
    _TASKS[task_id] = task
    return task


def _handle_tasks_get(params: dict) -> dict:
    task_id = params.get("id")
    if not task_id or task_id not in _TASKS:
        raise ValueError(f"task not found: {task_id}")
    return _TASKS[task_id]


@csrf_exempt
@require_http_methods(["POST"])
@require_a2a_bearer
def agent_jsonrpc(request, name: str):
    """POST /v1/agents/<name> — JSON-RPC tasks/send, tasks/get."""
    if _card.load_card(name, base_url=_base_url(request)) is None:
        return JsonResponse({"error": f"unknown agent: {name}"}, status=404)

    try:
        req = json.loads(request.body.decode() or "{}")
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"error": f"bad JSON: {e}"}, status=400)

    rpc_id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    # Tier 3 live dispatch: forward to orochi hub if this agent is
    # marked dispatchable. The canned-echo path below stays as the
    # fallback for agents not yet wired through to a real runtime.
    if method == "tasks/send" and _dispatch.is_dispatchable(name):
        code, payload = _dispatch.dispatch(name, req)
        if code == 200:
            return JsonResponse(payload, status=200)
        # Surface hub errors as JSON-RPC error envelopes so A2A clients
        # see a structured failure instead of an opaque HTTP code.
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {
                    "code": -32000,
                    "message": payload.get("error", f"hub HTTP {code}"),
                },
            },
            status=code if code >= 400 else 502,
        )

    try:
        if method == "tasks/send":
            result = _handle_tasks_send(name, params, _base_url(request))
        elif method == "tasks/get":
            result = _handle_tasks_get(params)
        else:
            return JsonResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {
                        "code": -32601,
                        "message": f"method not found: {method}",
                    },
                }
            )
    except Exception as e:  # noqa: BLE001 — JSON-RPC error envelope
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32000, "message": str(e)},
            }
        )

    return JsonResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})
