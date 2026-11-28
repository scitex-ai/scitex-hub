"""Serve files under ``MEDIA_ROOT`` through an authorisation check.

``/media/<path>`` used to be served straight from disk to anyone who knew
the path. This view applies :mod:`apps.infra.platform_app.services.media_access`
first and answers 404 (not 403) when the caller may not read the file, so the
existence of private files is not disclosed.

Behind nginx the bytes are handed off with ``X-Accel-Redirect`` to an
``internal`` location: nginx announces that location on every ``/media/``
request it proxies (``X-Media-Accel-Prefix``, always overwritten by nginx),
and the view only uses it when it is the configured one. Without nginx (dev
server, tests) the view streams the file itself.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import Http404
from django.views.decorators.http import require_GET

from apps.infra.platform_app.services.media_access import (
    is_public_media,
    may_read_media,
    normalise_media_path,
)
from apps.infra.platform_app.services.paths import resolve_within
from apps.user_content import user_file_response

#: Must match the ``internal`` location in the nginx configs.
ACCEL_PREFIX = "/_protected_media/"


def _resolve(path: str) -> Path:
    # resolve_within is the project's containment check (symlinks resolved,
    # component-wise), recognised as a path sanitiser by the CodeQL model.
    target = resolve_within(Path(settings.MEDIA_ROOT), path)
    if target is None or not target.is_file():
        raise Http404
    return target


@require_GET
def serve_media(request, path):
    rel = normalise_media_path(path)
    if rel is None or not may_read_media(request.user, request, rel):
        raise Http404
    target = _resolve(rel)
    public = is_public_media(rel)

    # Disposition, nosniff and the sandbox policy come from the shared
    # user-file helper, so media follows the same inline rules as every other
    # user file the Hub serves.
    if request.META.get("HTTP_X_MEDIA_ACCEL_PREFIX") == ACCEL_PREFIX:
        response = user_file_response(b"", target.name)
        relative = target.relative_to(Path(settings.MEDIA_ROOT).resolve()).as_posix()
        response["X-Accel-Redirect"] = ACCEL_PREFIX + quote(relative)
    else:
        response = user_file_response(open(target, "rb"), target.name)
    response["Cache-Control"] = (
        "public, max-age=604800" if public else "private, no-store"
    )
    if not public:
        response["X-Robots-Tag"] = "noindex, nofollow"
    return response
