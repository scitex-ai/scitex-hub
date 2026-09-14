#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give mounted leaf-app pages the same desktop content frame as hub pages.

Hub pages load ``site-content-frame.css`` from ``global_head_styles.html``.
Leaf apps such as Scholar's /apps/scholar/v2/ render scitex-ui's standalone
shell as their own HTML document, so no hub template runs; this middleware adds
the stylesheet link before ``</head>`` of those documents.
"""

from __future__ import annotations

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction

logger = logging.getLogger(__name__)

FRAME_STYLESHEET = "shared/css/layouts/site-content-frame.css"
STANDALONE_SHELL_MARKER = 'id="workspace-three-col"'


def is_standalone_leaf_page(request, response) -> bool:
    """Whether ``response`` is a full scitex-ui standalone-shell HTML page."""
    if getattr(response, "streaming", False) or response.get("Content-Encoding"):
        return False
    if response.status_code != 200:
        return False
    if "text/html" not in response.get("Content-Type", "").lower():
        return False
    headers = request.headers
    if headers.get("X-Requested-With") == "XMLHttpRequest" or headers.get("HX-Request"):
        return False
    return headers.get("Sec-Fetch-Dest", "") not in ("iframe", "frame", "embed", "object")


def inject_frame_stylesheet(request, response) -> None:
    """Add the frame stylesheet link to a standalone leaf page that lacks it."""
    if not is_standalone_leaf_page(request, response):
        return
    charset = response.charset or "utf-8"
    body = response.content.decode(charset, errors="ignore")
    if STANDALONE_SHELL_MARKER not in body or FRAME_STYLESHEET in body:
        return
    head_end = body.find("</head>")
    if head_end == -1:
        return

    from django.templatetags.static import static

    link = f'<link rel="stylesheet" href="{static(FRAME_STYLESHEET)}" />'
    data = (body[:head_end] + link + body[head_end:]).encode(charset)
    response.content = data
    if response.get("Content-Length") is not None:
        response["Content-Length"] = str(len(data))


class SiteContentFrameMiddleware:
    """Inject the desktop content-frame stylesheet into standalone leaf pages."""

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
        self._safe_inject(request, response)
        return response

    @staticmethod
    def _safe_inject(request, response):
        try:
            inject_frame_stylesheet(request, response)
        except Exception:
            # Layout polish must never break the page it decorates.
            logger.exception("[site-content-frame] injection failed for %s", request.path)


# EOF
