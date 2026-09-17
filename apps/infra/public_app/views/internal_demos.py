#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The staff demo index: a persistent progress list, because Telegram files vanish.

Why this page exists. Renders posted to chat disappear in the feed within days, so the
team cannot tell what exists, what state it is in, or why a take was rejected, and it
re-records work it already has. This page is the index of record: latest first, every
entry explicit, nothing inferred and nothing auto-promoted.

What an entry shows: the flow (scenario), its date, its status — Draft, Rejected or
Approved, exactly as the catalog says — which languages exist, the development commit it
was recorded against, the known product defects, and links to play and download it.
Rejected takes stay visible as history (the partial-light Brian draft is Rejected, not
deleted). The only filters are flow and status.

Who may see it. ``is_instance_admin`` — the same ``is_staff`` / ``is_superuser`` test the
hub applies to its other operator-only surfaces. Anonymous visitors are sent to sign in;
signed-in non-staff get 403. Outside the application, the deployment puts @scitex.ai
Access in front of /internal/*; that is not this module's job and it does not depend on it.

Status is never computed here. It comes from the catalog, which the pipeline writes when
it registers a render as Draft and only a person changes; this view cannot promote
anything.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    StreamingHttpResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from .. import clip_registry, demo_library
from .status.access import is_instance_admin

logger = logging.getLogger(__name__)

STAFF_ONLY_MESSAGE = (
    "The internal demo library is available to SciTeX staff and instance "
    "administrators. Ask an operator if you need access."
)

# The catalog is the list of record. A filesystem sweep is deliberately not used: an
# entry is something the pipeline registered, with a status a person owns.
CATALOG_FILENAME = "demos-catalog.json"


def library_directory():
    """Where internal media is read from; no fallback to the public media tree."""
    return getattr(settings, "DEMO_VIDEO_LIBRARY_DIR", None)


def catalog_path():
    """The catalog file, beside the library or wherever the setting points."""
    configured = getattr(settings, "DEMO_VIDEO_CATALOG", "") or ""
    if configured:
        from pathlib import Path

        return Path(configured)
    directory = library_directory()
    if not directory:
        return None
    from pathlib import Path

    return Path(directory) / CATALOG_FILENAME


def no_store(response):
    """Mark a staff-only response as uncacheable and unindexable."""
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def access_denied(request):
    """A response to send back instead of the library, or None when allowed."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        login_url = getattr(settings, "LOGIN_URL", "/auth/signin/")
        query = urlencode({"next": request.get_full_path()})
        return no_store(redirect(f"{login_url}?{query}"))
    if not is_instance_admin(user):
        return no_store(HttpResponseForbidden(STAFF_ONLY_MESSAGE))
    return None


def media_url(name: str, folder: str = "") -> str:
    """The authorized route for one file, folder-qualified when the render has one."""
    qualified = f"{folder}/{name}" if folder else name
    return reverse("public_app:internal_demo_media", kwargs={"name": qualified})


def card_for(clip: dict, directory) -> dict:
    """One row: what the catalog says, plus play and download links for its media.

    Nothing here changes a status. The languages, the defects and the commit are read
    from the catalog entry exactly as registered; the media links are derived from the
    manifest, and an entry whose files are gone simply has no links.
    """
    manifest_path = clip.get("manifest", "")
    folder, files = "", []
    try:
        from pathlib import Path

        if manifest_path and Path(manifest_path).exists():
            entry = demo_library.entry_for(Path(manifest_path), directory)
            folder = entry.get("folder", "")
            for rendition in entry.get("renditions", []):
                roles = rendition.get("files", {})
                for role in ("video", "captions"):
                    name = roles.get(role) or ""
                    if name:
                        files.append({
                            "language": rendition.get("language", ""),
                            "role": role,
                            "name": name,
                            "play_url": media_url(name, folder),
                            "download_url": media_url(name, folder) + "?download=1",
                        })
    except (OSError, ValueError) as error:      # a broken manifest is not a 500
        logger.warning("could not read %s: %s", manifest_path, error)

    return {
        "id": clip.get("id", ""),
        "flow": clip.get("scenario", ""),
        "title": clip.get("title") or {},
        "date": clip.get("date", ""),
        "status": clip.get("status", "draft"),
        "registered_at": clip.get("registered_at", ""),
        "languages": clip.get("languages", []),
        "viewports": clip.get("viewports", []),
        "dev_commit": clip.get("dev_commit", ""),
        "dev_commit_short": (clip.get("dev_commit") or "")[:12],
        "dev_branch": clip.get("dev_branch", ""),
        "defects": clip.get("defects") or [],
        "rejection": clip.get("rejection") or {},
        "watch": clip.get("watch") or {},
        "files": files,
    }


def index_view(request):
    """Latest first, filters for flow and status only, rejected history included."""
    denial = access_denied(request)
    if denial is not None:
        return denial

    directory = library_directory()
    path = catalog_path()
    catalog = {"clips": []}
    if path is not None:
        try:
            catalog = clip_registry.load_catalog(path)
        except (clip_registry.ClipError, OSError) as error:
            logger.warning("catalog %s unreadable: %s", path, error)

    cards = [card_for(clip, directory) for clip in catalog.get("clips", [])]
    flows = sorted({card["flow"] for card in cards if card["flow"]})
    statuses = list(clip_registry.STATUSES)

    selected_flow = (request.GET.get("flow") or "").strip()
    selected_status = (request.GET.get("status") or "").strip()
    if selected_flow:
        cards = [card for card in cards if card["flow"] == selected_flow]
    if selected_status:
        cards = [card for card in cards if card["status"] == selected_status]

    # Latest first: a progress index reads from the top. Registered time breaks a tie, so
    # a re-render of the same day's scenario sorts above the take it replaced.
    cards.sort(key=lambda card: (card["date"], card["registered_at"]), reverse=True)

    counts = dict.fromkeys(statuses, 0)
    for card in cards:
        counts[card["status"]] = counts.get(card["status"], 0) + 1

    return no_store(render(
        request,
        "public_app/pages/internal_demos.html",
        {
            "cards": cards,
            "counts": counts,
            "flows": flows,
            "statuses": statuses,
            "selected_flow": selected_flow,
            "selected_status": selected_status,
            "total": len(cards),
            "staff_only_message": STAFF_ONLY_MESSAGE,
            "catalog_path": str(path) if path else "",
        },
    ))


def file_slice(path, start: int, end: int, block: int = 64 * 1024):
    """Yield exactly the bytes in ``[start, end]``, in bounded blocks."""
    remaining = end - start + 1
    with open(path, "rb") as handle:
        handle.seek(start)
        while remaining > 0:
            chunk = handle.read(min(block, remaining))
            if not chunk:
                return
            remaining -= len(chunk)
            yield chunk


def media_view(request, name):
    """Serve one library file to staff, and never from a public path.

    ``?download=1`` asks for the same bytes as a file rather than as a stream; the entry
    checks, the containment and the cache rules are identical either way.
    """
    denial = access_denied(request)
    if denial is not None:
        return denial

    directory = library_directory()
    path = demo_library.resolve_media(directory, name) if directory else None
    if path is None:
        logger.info("internal demo media refused: %r", name)
        raise Http404("No such internal demo asset")

    download = request.GET.get("download") in ("1", "true", "yes")
    content_type = demo_library.content_type_for(name)
    size = path.stat().st_size
    bounds = demo_library.range_bounds(request.headers.get("Range", ""), size)
    if bounds == "unsatisfiable":
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{size}"
    elif isinstance(bounds, tuple):
        start, end = bounds
        response = StreamingHttpResponse(
            file_slice(path, start, end), status=206, content_type=content_type
        )
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        response["Content-Length"] = str(end - start + 1)
    else:
        response = FileResponse(open(path, "rb"), content_type=content_type)
        response["Content-Length"] = str(size)
    if download:
        from urllib.parse import quote

        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(path.name)}"
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


# The names the URLconf and the routing tests use.
internal_demos = index_view
internal_demo_media = media_view


# EOF
