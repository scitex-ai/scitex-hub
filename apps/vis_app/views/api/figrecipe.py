"""figrecipe editor API views for Django.

Mirrors figrecipe's Flask route handlers, calling the same Python
functions directly. Handlers are in figrecipe_handlers/.
"""

import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ...services.figrecipe_editor import (
    get_editor_html,
    get_or_create_editor,
    make_session_key,
)
from .figrecipe_handlers import HANDLERS, handle_download_fig, handle_single_call

logger = logging.getLogger(__name__)


def _inject_project_context(request):
    """Inject working_dir from user's current project into GET params.

    This allows the figrecipe API to resolve recipe paths relative to the
    user's project directory, without the browser seeing absolute paths.
    """
    from apps.project_app.services.project_utils import get_current_project

    if not request.user.is_authenticated:
        return
    if request.GET.get("working_dir"):
        return  # Already set (e.g. by vis_react proxy)

    project = get_current_project(request, user=request.user)
    if project:
        mutable_get = request.GET.copy()
        mutable_get["working_dir"] = str(project.get_local_path())
        request.GET = mutable_get


def _get_editor(request):
    """Extract recipe_path and return cached editor."""
    import json

    _inject_project_context(request)

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
    if handler:
        try:
            return handler(request, editor)
        except Exception as e:
            logger.exception("[Vis] figrecipe API error on /%s", endpoint)
            return JsonResponse({"error": str(e)}, status=500)

    # Parameterized endpoints: call/<call_id> and download/<fmt>
    if endpoint.startswith("call/"):
        call_id = endpoint[5:]
        try:
            return handle_single_call(request, editor, call_id)
        except Exception as e:
            logger.exception("[Vis] figrecipe API error on /call/%s", call_id)
            return JsonResponse({"error": str(e)}, status=500)

    if endpoint.startswith("download/"):
        fmt = endpoint[9:]
        try:
            return handle_download_fig(request, editor, fmt)
        except Exception as e:
            logger.exception("[Vis] figrecipe API error on /download/%s", fmt)
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": f"Unknown endpoint: {endpoint}"}, status=404)
