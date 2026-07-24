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
a caller-chosen path through).

The figrecipe dispatch additionally keys file resolution on SEVERAL
caller-controlled path parameters, from BOTH the query string and the JSON
body (enumerated from ``figrecipe/_django/{views.py,handlers/}``):

  * ``recipe`` / ``recipe_path`` — editor bootstrap opens the recipe
    verbatim (``get_or_create_editor``).
  * ``path`` — ``api/switch``/``new``/``delete``/``rename``/``duplicate``/
    ``download`` join it to ``working_dir`` (``working_dir / path``).
  * ``file_path`` — ``api/file-content`` joins it to the working dir.

pathlib's ``/`` DISCARDS the left operand when the right side is ABSOLUTE,
so an absolute value escapes the server-forced ``working_dir`` entirely;
and a RELATIVE ``../`` value climbs out of the jail. The guard therefore
resolves the join for EVERY such parameter and requires component-wise
containment in the caller's OWN data jail — ``(working_dir / value)
.resolve()`` collapses ``..`` and lands an absolute value outside the jail,
so the single check closes both escapes. Fails closed (403) on any escape.
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


# Every request parameter figrecipe's dispatch may interpret as a
# filesystem path — from the query string OR the JSON body. Each one is a
# containment sink (joined to working_dir and/or opened verbatim by the
# package), so the guard validates the RESOLVED join of ALL of them, not
# one hand-picked param. Enumerated from
# figrecipe/_django/views.py (``recipe``/``recipe_path`` -> editor bootstrap)
# and figrecipe/_django/handlers/files.py (``path`` -> switch/new/delete/
# rename/duplicate/download; ``file_path`` -> file-content).
_PATH_PARAMS = ("path", "recipe", "recipe_path", "file_path")


def _iter_candidate_path_values(request):
    """Yield ``(key, value)`` for every path-bearing param in GET + body."""
    seen = []
    for key in _PATH_PARAMS:
        val = request.GET.get(key)
        if isinstance(val, str) and val:
            seen.append((key, val))
    if request.method != "GET" and getattr(request, "body", b""):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError, TypeError):
            data = {}
        if isinstance(data, dict):
            for key in _PATH_PARAMS:
                val = data.get(key)
                if isinstance(val, str) and val:
                    seen.append((key, val))
    return seen


def _reject_out_of_jail_paths(request):
    """Return a 403 when ANY path-bearing param escapes the caller's jail.

    Generic and COMPLETE: for every path parameter the figrecipe dispatch
    consumes (``path``/``recipe``/``recipe_path``/``file_path``), from BOTH
    the query string and the JSON body, compute the RESOLVED join against
    the server-forced ``working_dir`` and require component-wise containment
    in the user's own data jail via ``validate_path_in_user_jail``.

    ``.resolve()`` collapses ``..`` AND (because pathlib's ``/`` keeps an
    absolute right-hand operand verbatim, discarding ``working_dir``) lands
    an absolute value outside the jail — so this ONE check rejects both an
    absolute path and a ``../`` traversal. Returns ``None`` (no block) only
    when every candidate is contained. Fails closed.
    """
    candidates = _iter_candidate_path_values(request)
    if not candidates:
        return None

    from apps.infra.project_app.services.filesystem.permissions import (
        validate_path_in_user_jail,
    )

    working_dir = request.GET.get("working_dir")

    for key, value in candidates:
        if working_dir:
            candidate = (Path(working_dir) / value).resolve()
        else:
            # The wrapper overrides working_dir from the server-side project
            # before this guard runs, so this branch is defensive only;
            # validating the raw value still fails closed on absolute / ``..``.
            candidate = Path(value).resolve()
        if not validate_path_in_user_jail(request.user, candidate):
            logger.warning(
                "[figrecipe] rejecting out-of-jail %s=%r from user %s",
                key,
                value,
                getattr(request.user, "username", "?"),
            )
            return JsonResponse(
                {"error": "path is outside your workspace"}, status=403
            )
    return None


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
    guard=_reject_out_of_jail_paths,
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
