"""
Web app context API for AI agents.

Exposes the same context that terminal agents get via SKILL.md,
but as a queryable HTTP endpoint. Called by scitex_cloud MCP tools
(cloud_get_context, cloud_eval_js, cloud_ui_action).
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.llm_app.skills import (
    build_aggregated_context,
    get_all_skills,
    get_skill_for_page,
)
from apps.llm_app.views.skills import _serialize_skill


@login_required
@require_http_methods(["GET"])
def api_get_context(request):
    """Return aggregated web app context for AI agents.

    Query params:
        page: Current page URL (e.g. /writer/)
    """
    page = request.GET.get("page", "")

    active_skill = get_skill_for_page(page) if page else None
    all_skills = get_all_skills()

    return JsonResponse(
        {
            "success": True,
            "username": request.user.username,
            "page": page,
            "active_skill": _serialize_skill(active_skill) if active_skill else None,
            "all_skills": {n: _serialize_skill(s) for n, s in all_skills.items()},
            "available_actions": [
                "navigate",
                "highlight",
                "click",
                "fill",
                "scroll",
                "clear",
            ],
            "media_rendering": [
                "png",
                "jpg",
                "svg",
                "gif",
                "csv",
                "tsv",
                "pdf",
                "mmd",
            ],
            "aggregated_context": build_aggregated_context(),
        }
    )


@login_required
@require_http_methods(["POST"])
async def api_eval_js(request):
    """Evaluate JavaScript in the user's browser via WebSocket relay.

    Sends JS code to the user's browser through Django Channels,
    waits for the result, and returns it.

    POST body: {"code": "document.title", "timeout": 10}
    """
    import asyncio
    import uuid

    from channels.layers import get_channel_layer

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    code = data.get("code", "").strip()
    if not code:
        return JsonResponse({"success": False, "error": "code is required"}, status=400)

    timeout = min(data.get("timeout", 10), 30)  # Cap at 30s
    request_id = str(uuid.uuid4())[:8]
    username = request.user.username
    group_name = f"eval_js_{username}"
    result_key = f"eval_js_result_{request_id}"

    try:
        channel_layer = get_channel_layer()

        # Send eval request to browser
        await channel_layer.group_send(
            group_name,
            {
                "type": "eval_js",
                "code": code,
                "request_id": request_id,
            },
        )

        # Wait for result via cache (browser sends result back to Django)
        from django.core.cache import cache

        for _ in range(timeout * 10):  # Check every 100ms
            result = cache.get(result_key)
            if result is not None:
                cache.delete(result_key)
                return JsonResponse({"success": True, "result": result})
            await asyncio.sleep(0.1)

        return JsonResponse(
            {"success": False, "error": f"Timeout after {timeout}s"},
            status=408,
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
async def api_ui_action(request):
    """Relay UI action to the user's browser via WebSocket.

    POST body: {"steps": [...], "delay_ms": 900}
    """
    from channels.layers import get_channel_layer

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    steps = data.get("steps", [])
    if not steps:
        return JsonResponse(
            {"success": False, "error": "steps is required"}, status=400
        )

    delay_ms = data.get("delay_ms", 900)
    username = request.user.username
    group_name = f"eval_js_{username}"

    try:
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            group_name,
            {
                "type": "ui_action",
                "steps": steps,
                "delay_ms": delay_ms,
            },
        )
        return JsonResponse({"success": True, "steps_sent": len(steps)})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
