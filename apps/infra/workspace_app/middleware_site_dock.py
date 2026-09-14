#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Put the site-wide dock on leaf-app pages that do not extend global_base.html.

Hub pages get the dock from ``global_base.html`` (``{% site_dock %}``). Mounted
leaf apps such as Scholar's /apps/scholar/v2/ are served as the leaf package's
OWN HTML document (scitex-app's host view factory), so no hub template is ever
involved and the base-template dock cannot reach them. The operator asked for
the dock on EVERY page (2026-09-14), so this middleware appends the same partial
before ``</body>`` of any such document.

Modelled on ``scitex_ui.middleware.ElementInspectorMiddleware`` (already in
MIDDLEWARE): async-capable, touches only non-streaming, un-encoded ``text/html``
200 responses, and never raises into a response.

It stays out of the way of:
  * a page that already has the dock (the ``data-site-dock`` marker), so hub
    pages are never given two;
  * anonymous requests (every dock target requires sign-in);
  * fragments and embeds: XHR / htmx requests, ``Sec-Fetch-Dest: iframe``, and
    any document without ``</body>``;
  * the Django admin.
"""

from __future__ import annotations

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

from .site_dock import DOCK_MARKER, should_render_dock

logger = logging.getLogger(__name__)

_FONT_AWESOME = (
    '<link rel="stylesheet" '
    'href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />'
)


def wants_dock(request, response) -> bool:
    """Whether ``response`` is a full signed-in HTML page that lacks the dock."""
    if getattr(response, "streaming", False) or response.get("Content-Encoding"):
        return False
    if response.status_code != 200:
        return False
    if "text/html" not in response.get("Content-Type", "").lower():
        return False
    if request.path.startswith("/admin/"):
        return False
    headers = request.headers
    if headers.get("X-Requested-With") == "XMLHttpRequest" or headers.get("HX-Request"):
        return False
    if headers.get("Sec-Fetch-Dest", "") in ("iframe", "frame", "embed", "object"):
        return False
    return should_render_dock(request)


def inject_dock(request, response) -> None:
    """Append the dock partial before ``</body>`` (no-op when not applicable)."""
    if not wants_dock(request, response):
        return
    charset = response.charset or "utf-8"
    body = response.content.decode(charset, errors="ignore")
    if DOCK_MARKER in body:
        return
    idx = body.rfind("</body>")
    if idx == -1:
        return

    from django.template.loader import render_to_string

    from apps.infra.public_app.templatetags.site_dock import dock_context

    snippet = render_to_string(
        "global_base_partials/site_dock.html", dock_context(request)
    )
    if "font-awesome" not in body:
        # The dock's glyphs are Font Awesome; a leaf page may not load it.
        snippet = _FONT_AWESOME + snippet
    data = (body[:idx] + snippet + body[idx:]).encode(charset)
    response.content = data
    if response.get("Content-Length") is not None:
        response["Content-Length"] = str(len(data))


class SiteDockMiddleware:
    """Inject the site-wide dock into full HTML pages that did not render it."""

    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            markcoroutinefunction(self)

    def __call__(self, request):
        if self.async_mode:
            return self.__acall__(request)
        response = self.get_response(request)
        self._safe_inject(request, response)
        return response

    async def __acall__(self, request):
        response = await self.get_response(request)
        # request.user is lazy and DB-backed: resolve it off the event loop.
        await sync_to_async(self._safe_inject)(request, response)
        return response

    @staticmethod
    def _safe_inject(request, response):
        try:
            inject_dock(request, response)
        except Exception:
            # Navigation chrome must never break the page it decorates.
            logger.exception("[site-dock] injection failed for %s", request.path)


# EOF
