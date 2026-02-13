"""figrecipe editor API views for Django.

Mirrors figrecipe's Flask route handlers, calling the same Python
functions directly. Handlers are in figrecipe_handlers.py.
"""

import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ...services.figrecipe_editor import (
    get_editor_html,
    get_or_create_editor,
    make_session_key,
)
from .figrecipe_handlers import HANDLERS

logger = logging.getLogger(__name__)


def _get_editor(request):
    """Extract recipe_path and return cached editor."""
    import json

    if request.method == "GET":
        recipe_path = request.GET.get("recipe", "")
    else:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}
        recipe_path = data.get("recipe_path", "") or request.GET.get("recipe", "")

    if not recipe_path:
        return None, "Missing recipe path"

    user_id = request.user.id if request.user.is_authenticated else 0
    session_key = make_session_key(user_id, recipe_path)
    editor = get_or_create_editor(session_key, recipe_path)
    return editor, None


# ─── Main editor page ───────────────────────────────────────────


def figrecipe_editor_page(request):
    """Serve figrecipe's complete HTML editor page."""
    editor, err = _get_editor(request)
    if err:
        return HttpResponse(f"<h3>Error: {err}</h3>", status=400)

    dark_mode = request.GET.get("dark", "false").lower() == "true"
    html = get_editor_html(editor, "/vis/figrecipe", dark_mode=dark_mode)
    return HttpResponse(html)


# ─── Catch-all API dispatcher ───────────────────────────────────


@csrf_exempt
def figrecipe_api(request, endpoint):
    """Dispatch figrecipe API calls to handler functions."""
    editor, err = _get_editor(request)
    if err:
        return JsonResponse({"error": err}, status=400)

    handler = HANDLERS.get(endpoint)
    if not handler:
        return JsonResponse({"error": f"Unknown endpoint: {endpoint}"}, status=404)

    try:
        return handler(request, editor)
    except Exception as e:
        logger.exception("[Vis] figrecipe API error on /%s", endpoint)
        return JsonResponse({"error": str(e)}, status=500)
