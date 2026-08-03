"""Vis app URLs - figrecipe editor integration.

Delegates to figrecipe._django with project-context injection.

SECURITY (card sec-working-dir-passthrough-family, SITE 2)
----------------------------------------------------------
This mount used to be COMPLETELY UNAUTHENTICATED: neither the editor page
nor the API dispatcher carried ``@login_required``, so an anonymous
internet caller could drive figrecipe's file handlers against the host
filesystem. Both routes are now ``@login_required``.

``working_dir`` is derived from the authenticated user's current project
and OVERWRITES any caller-supplied value (it used to early-return and pass
a caller-chosen path through). Note figrecipe additionally keys file
resolution on ``?recipe=`` / JSON ``recipe_path``; an ABSOLUTE recipe path
is opened verbatim by the package (``Path(recipe_path)``), so the api guard
rejects any absolute recipe that escapes the caller's own workspace jail.
Fails closed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import path
from figrecipe._django.views import api_dispatch as _raw_api_dispatch
from figrecipe._django.views import editor_page as _raw_editor_page

from apps.infra.project_app.services.working_dir_resolver import (
    WorkingDirScopedView,
)

logger = logging.getLogger(__name__)


def _extract_recipe(request) -> str:
    """Recipe path the package would open, from GET or JSON body.

    Mirrors figrecipe._django.views._get_recipe_path so the value we
    validate is the value the package actually resolves.
    """
    if request.method == "GET":
        return request.GET.get("recipe", "") or ""
    try:
        data = json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        data = {}
    return data.get("recipe_path", "") or request.GET.get("recipe", "") or ""


def _reject_out_of_jail_recipe(request):
    """Return a 403 when an ABSOLUTE ?recipe= escapes the user's own jail.

    Relative recipe paths are left to the package (resolved within the
    working_dir we override server-side); an absolute path, however, is
    opened as-is by the package, so it is the caller-controlled sink we
    must contain here. Returns ``None`` (no block) otherwise.
    """
    recipe = _extract_recipe(request)
    if not recipe:
        return None
    p = Path(recipe)
    if not p.is_absolute():
        return None

    from apps.infra.project_app.services.filesystem.permissions import (
        validate_path_in_user_jail,
    )

    if validate_path_in_user_jail(request.user, p):
        return None
    logger.warning(
        "[figrecipe] rejecting out-of-jail absolute recipe from user %s",
        getattr(request.user, "username", "?"),
    )
    return JsonResponse(
        {"error": "recipe path is outside your workspace"}, status=403
    )


def _no_project_json(request):
    return JsonResponse(
        {
            "error": (
                "No active project resolved for your account. Create "
                "or open a project first."
            ),
            "hint": "/new/",
        },
        status=404,
    )


# Editor page reads its working dir from an env var inside the package;
# login_required is the load-bearing guard here (closes the anonymous
# hole). We still inject best-effort (fail_closed=False) so a GET-derived
# working_dir is scoped, harmlessly, without blocking the SPA shell.
_editor_view = WorkingDirScopedView(_raw_editor_page, fail_closed=False)
_api_view = WorkingDirScopedView(
    _raw_api_dispatch,
    on_missing=_no_project_json,
    guard=_reject_out_of_jail_recipe,
)


@login_required
def editor_page(request):
    return _editor_view(request)


@login_required
def api_dispatch_with_context(request, endpoint):
    """Wrap figrecipe._django.views.api_dispatch with project context."""
    return _api_view(request, endpoint)


urlpatterns = [
    path("figrecipe/", editor_page, name="figrecipe_editor"),
    path(
        "figrecipe/<path:endpoint>",
        api_dispatch_with_context,
        name="figrecipe_api",
    ),
]


# EOF
