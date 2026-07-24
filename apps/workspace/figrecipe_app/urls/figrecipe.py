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

figrecipe's dispatch reads a caller-controlled filesystem path from THREE
distinct channels — the query string, the JSON body, AND the URL
``<path:endpoint>`` SEGMENT (enumerated from
``figrecipe/_django/{views.py,handlers/}``). The guard validates ALL three
against the caller's OWN data jail and fails closed (403) on any escape:

  CHANNEL 1+2 — query / body, joined to ``working_dir`` (or opened verbatim
    when absolute):
      * ``recipe`` / ``recipe_path`` — editor bootstrap opens the recipe
        verbatim (``get_or_create_editor``).
      * ``path`` — ``api/switch``/``new``/``delete``/``rename``/``duplicate``
        / ``download`` join it to ``working_dir`` (``working_dir / path``).
    pathlib's ``/`` DISCARDS the left operand when the right side is
    ABSOLUTE, so an absolute value escapes the server-forced ``working_dir``;
    and a RELATIVE ``../`` value climbs out. ``(working_dir / value)
    .resolve()`` collapses ``..`` and lands an absolute value outside the
    jail, so the single component-wise containment check closes both.

  CHANNEL 2 — body sinks whose base is NOT ``working_dir`` (endpoint-gated,
    so a same-named key on another endpoint is never mis-validated):
      * ``api/compose`` writes ``Path(working_dir) / f"{filename}.png"`` with
        the BODY ``working_dir`` used VERBATIM — the GET override never
        touches the JSON body, so an absolute/``..`` body value is an
        arbitrary host-directory WRITE. The exact resolved out-path is
        jailed.
      * ``api/gallery/add`` reads ``_EXAMPLES_DIR / f"{template}.yaml"`` and
        ``add_image_from_url`` fetches ``url`` via ``urllib`` (``file://`` is
        a local-file READ). ``template`` is contained to a relative subtree;
        ``url`` is restricted to ``http(s)``.

  CHANNEL 3 — the URL ``<path:endpoint>`` segment (NEVER seen by a
    query/body guard):
      * ``api/file-content/<remainder>`` — resolved against
        ``_find_default_working_dir()`` == the process cwd == ``BASE_DIR``
        (``/app``) on the server; the package's own check is a
        ``str.startswith(cwd)`` that CONTAINS every tenant
        (``BASE_DIR/data/users/*``), so an absolute or ``../`` remainder
        reads a VICTIM's file cross-tenant. Jailed to the caller's own root.
      * ``api/gallery/thumbnail/<name>`` — reads ``_EXAMPLES_DIR /
        f"{name}.png"`` (a ``../`` climb escapes that read-only package dir);
        contained to a relative subtree.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import path
from figrecipe._django.views import api_dispatch as _raw_api_dispatch
from figrecipe._django.views import editor_page as _raw_editor_page

from apps.infra.project_app.services.working_dir_resolver import (
    WorkingDirScopedView,
)

logger = logging.getLogger(__name__)


# CHANNEL 1+2: query/body params figrecipe resolves RELATIVE TO working_dir
# (or opens verbatim when absolute). Each is a containment sink validated by
# the resolved-join + user-jail check.
#
# ``file_path`` is deliberately ABSENT: NO handler reads a GET/body key of
# that name. ``api/file-content`` derives its path from the URL
# ``<path:endpoint>`` SEGMENT (Channel 3), so the former ``file_path`` entry
# was DEAD — it matched nothing the package reads. Channel 3 handles it.
_PATH_PARAMS = ("path", "recipe", "recipe_path")

# CHANNEL 3 URL-segment prefixes (mirrors the slicing in
# figrecipe/_django/views.api_dispatch: ``endpoint[len(prefix):]``).
_FILE_CONTENT_PREFIX = "api/file-content/"
_THUMBNAIL_PREFIX = "api/gallery/thumbnail/"


def _parse_body(request):
    """Return the JSON body as a dict (``{}`` for GET / absent / non-JSON)."""
    if request.method == "GET" or not getattr(request, "body", b""):
        return {}
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _iter_candidate_path_values(request, body):
    """Yield ``(key, value)`` for every working_dir-relative path param."""
    seen = []
    for key in _PATH_PARAMS:
        val = request.GET.get(key)
        if isinstance(val, str) and val:
            seen.append((key, val))
    for key in _PATH_PARAMS:
        val = body.get(key)
        if isinstance(val, str) and val:
            seen.append((key, val))
    return seen


def _within_relative_subtree(value: str) -> bool:
    """True iff ``value`` is a RELATIVE path with no ``..`` escape.

    Base-independent containment for the read-only package-directory read
    sinks (``api/gallery/{thumbnail,add}``) whose base is figrecipe's
    examples dir. That dir ships no symlinks, so "not absolute AND no ``..``
    component" guarantees the resolved path stays within it — without this
    Django wrapper importing the package's private ``_EXAMPLES_DIR``.
    """
    p = Path(value)
    return not p.is_absolute() and ".." not in p.parts


def _forbid(key, value, username):
    """Log and return the canonical fail-closed 403 for an escape."""
    logger.warning(
        "[figrecipe] rejecting out-of-jail %s=%r from user %s",
        key,
        value,
        username,
    )
    return JsonResponse({"error": "path is outside your workspace"}, status=403)


def _reject_out_of_jail_paths(request, endpoint=None):
    """Return a 403 when ANY caller-controlled path escapes the caller's jail.

    Generic and COMPLETE: validates every path-bearing input across all
    THREE channels figrecipe's dispatch consumes — the query string, the
    JSON body, and the URL ``<path:endpoint>`` segment — via component-wise
    containment in the user's own data jail (``validate_path_in_user_jail``).
    Returns ``None`` (no block) ONLY when every candidate is contained; fails
    closed on the first escape.

    ``endpoint`` is the ``<path:endpoint>`` URL capture, forwarded by
    ``WorkingDirScopedView`` alongside the request (``None`` when the guard
    is invoked without it — defensive).
    """
    from apps.infra.project_app.services.filesystem.permissions import (
        validate_path_in_user_jail,
    )

    username = getattr(request.user, "username", "?")
    body = _parse_body(request)

    # -- CHANNEL 1+2: working_dir-relative params (join + resolve) --------
    working_dir = request.GET.get("working_dir")
    for key, value in _iter_candidate_path_values(request, body):
        if working_dir:
            candidate = (Path(working_dir) / value).resolve()
        else:
            # The wrapper overrides working_dir from the server-side project
            # before this guard runs, so this branch is defensive only;
            # validating the raw value still fails closed on absolute / ``..``.
            candidate = Path(value).resolve()
        if not validate_path_in_user_jail(request.user, candidate):
            return _forbid(key, value, username)

    # -- CHANNEL 2: endpoint-specific body sinks (base != working_dir) ----
    if endpoint == "api/compose":
        # handle_compose_save WRITES Path(working_dir) / f"{filename}.png"
        # with the BODY working_dir used verbatim. Validate the EXACT
        # resolved out-path so neither an absolute working_dir nor a ``..``
        # in filename can land the write outside the jail.
        body_wd = body.get("working_dir")
        if isinstance(body_wd, str) and body_wd:
            name = body.get("filename")
            if not isinstance(name, str) or not name:
                name = "composed"
            out_path = (Path(body_wd) / f"{name}.png").resolve()
            if not validate_path_in_user_jail(request.user, out_path):
                return _forbid("working_dir", body_wd, username)
    elif endpoint == "api/gallery/add":
        template = body.get("template")
        if (
            isinstance(template, str)
            and template
            and not _within_relative_subtree(template)
        ):
            return _forbid("template", template, username)
    elif endpoint == "add_image_from_url":
        # urllib.urlopen SUPPORTS file:// (arbitrary local-file READ / SSRF).
        # Inline images use the separate base64 ``add_image_panel`` endpoint,
        # so remote fetch is legitimately http(s) only.
        url = body.get("url")
        if isinstance(url, str) and url:
            if urlparse(url).scheme.lower() not in ("http", "https"):
                return _forbid("url", url, username)

    # -- CHANNEL 3: URL ``<path:endpoint>`` segment path sinks ------------
    if endpoint and endpoint.startswith(_FILE_CONTENT_PREFIX):
        remainder = endpoint[len(_FILE_CONTENT_PREFIX):]
        # handle_api_file_content resolves against _find_default_working_dir()
        # == process cwd == settings.BASE_DIR (/app) on the server. Its own
        # jail is startswith(cwd) which CONTAINS every tenant; re-check
        # against the caller's OWN data root instead.
        candidate = (Path(settings.BASE_DIR) / remainder).resolve()
        if not validate_path_in_user_jail(request.user, candidate):
            return _forbid("api/file-content", remainder, username)
    elif endpoint and endpoint.startswith(_THUMBNAIL_PREFIX):
        remainder = endpoint[len(_THUMBNAIL_PREFIX):]
        if remainder and not _within_relative_subtree(remainder):
            return _forbid("api/gallery/thumbnail", remainder, username)

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
