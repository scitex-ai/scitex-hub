#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The staff-only demo library: an index of what the team has recorded.

Why a page and not a folder listing. The rendered guides live on the media volume
where the public player can also reach them; the ones that are not publishable — a
Japanese rendition nobody has watched, a render whose scenario has moved, media
somebody replaced by hand — have no public home, and keeping them only in a chat
thread is how a team re-renders something it already had.

Who may see it. ``is_instance_admin`` — the same ``is_staff`` / ``is_superuser``
test the hub already applies to its other operator-only surfaces (host metrics,
billing admin, the SAC fleet mount). There is no shared page password: an
anonymous visitor is sent to sign in, and a signed-in non-staff account is
refused. Same reasoning as ``views/status/access.py``: the check is a plain
function called INSIDE each view, not a decorator, because routing tests assert
``resolve(path).func is <view>`` and a wrapper breaks that identity.

Why the media is not a static URL. ``/media/`` is served by the deployment to
anyone who knows the path, so internal assets go through ``internal_demo_media``
instead: authorized, name-sanitized by ``demo_library.resolve_media`` (which
rejects separators, parent segments, hidden and absolute names, and anything that
resolves outside the library directory), and answered with
``Cache-Control: private, no-store`` so no shared cache holds a copy.

The outer edge (Cloudflare Access for ``/internal/*``) is a separate, currently
unauthorized piece of work — see card hub-internal-demo-video-library-20260917.
This module is the inner gate and does not depend on it.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from .. import demo_library
from .status.access import is_instance_admin

logger = logging.getLogger(__name__)

STAFF_ONLY_MESSAGE = (
    "The internal demo library is available to SciTeX staff and instance "
    "administrators. Ask an operator if you need access."
)


def library_directory():
    """Where the internal library reads from (a directory of renders + sidecars).

    There is no fallback to ``MEDIA_ROOT``: that tree is served publicly to anyone
    who knows a path, and reading unpublished renders from it would quietly make
    them public. An unset setting means "no library", not "read the public one".
    """
    return getattr(settings, "DEMO_VIDEO_LIBRARY_DIR", None)


def access_denied(request):
    """A response to send back instead of the library, or None when allowed.

    Anonymous callers are sent to the existing sign-in flow with ``next`` so they
    land back here; signed-in non-staff callers get 403, because there is nothing
    for them to sign into.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        login_url = getattr(settings, "LOGIN_URL", "/auth/signin/")
        query = urlencode({"next": request.get_full_path()})
        return redirect(f"{login_url}?{query}")
    if not is_instance_admin(user):
        return HttpResponseForbidden(STAFF_ONLY_MESSAGE)
    return None


def _media_url(name: str) -> str:
    return reverse("public_app:internal_demo_media", kwargs={"name": name})


def with_media_urls(entry: dict) -> dict:
    """Point each rendition's files at the authorized route, not a static path."""
    for row in entry.get("renditions", []):
        row["urls"] = {
            role: _media_url(name) for role, name in (row.get("files") or {}).items() if name
        }
    entry["media_urls"] = {name: _media_url(name) for name in demo_library.media_names(entry)}
    return entry


def internal_demos(request):
    """The library index: one card per render, with its derived visibility."""
    denial = access_denied(request)
    if denial is not None:
        return denial

    directory = library_directory()
    if directory is None:
        logger.warning("DEMO_VIDEO_LIBRARY_DIR and MEDIA_ROOT are both unset")
        index = {"directory": "", "entries": [], "counts": {}, "total": 0}
    else:
        index = demo_library.library_index(directory)
    index["entries"] = [with_media_urls(entry) for entry in index["entries"]]
    return render(
        request,
        "public_app/pages/internal_demos.html",
        {
            "library": index,
            "staff_only_message": STAFF_ONLY_MESSAGE,
        },
    )


def internal_demo_media(request, name):
    """Serve one library file to staff, and never from a public path."""
    denial = access_denied(request)
    if denial is not None:
        return denial

    directory = library_directory()
    path = demo_library.resolve_media(directory, name) if directory else None
    if path is None:
        # A refused name and a missing file are the same answer on purpose: this
        # route should not confirm which internal names exist to a caller who had
        # to be authorized to reach it in the first place.
        logger.info("internal demo media refused: %r", name)
        raise Http404("No such internal demo asset")

    response = FileResponse(open(path, "rb"), content_type=demo_library.content_type_for(name))
    # Not a public asset: no shared cache may keep a copy, and the browser may not
    # treat it as immutable the way it treats /media/.
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


# EOF
