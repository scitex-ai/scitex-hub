#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give mounted leaf-app pages the same desktop content frame as hub pages.

Hub pages load ``site-content-frame.css`` from ``global_head_styles.html``.
Leaf apps such as Scholar's /apps/scholar/v2/ render scitex-ui's standalone
shell as their own HTML document, so no hub template runs; this middleware adds
the stylesheet link before ``</head>`` of those documents.
"""

from __future__ import annotations

import html
import logging
import re

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

logger = logging.getLogger(__name__)

FRAME_STYLESHEET = "shared/css/layouts/site-content-frame.css"
LEAF_CHROME_STYLESHEET = "shared/css/layouts/leaf-host-chrome.css"
LEAF_DEFAULT_FAVICON = "scitex_ui/img/scitex-favicon.svg"
STANDALONE_SHELL_MARKER ='id="workspace-three-col"'
LEAF_HEADER_MARKER = "data-leaf-site-header"
# Leaves that draw their own top bar (Scholar v2) keep it instead of a second one.
OWN_HEADER_MARKERS = ('class="app-header"', 'class="global-header"')


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


def _leaf_header(request, body: str) -> str:
    """The hub site header for a leaf page, or "" when the page brings its own."""
    if request.GET.get("embed") == "1" or LEAF_HEADER_MARKER in body:
        return ""
    if any(marker in body for marker in OWN_HEADER_MARKERS):
        return ""
    from django.template.loader import render_to_string

    match = re.search(r"<title>(.*?)</title>", body, re.S)
    title = html.unescape(match.group(1)).strip() if match else ""
    from config.context_processors import scitex_env

    try:
        return render_to_string(
            "global_base_partials/leaf_site_header.html",
            {"leaf_app_title": title, **scitex_env(request)},
        )
    except Exception:
        logger.exception("[site-content-frame] leaf header failed for %s", request.path)
        return ""


def _hub_favicon(request, body: str) -> str:
    """Swap scitex-ui's default tab icon for the hub's so a leaf tab matches its header logo."""
    from django.templatetags.static import static

    from config.context_processors import scitex_env

    default_href = static(LEAF_DEFAULT_FAVICON)
    if f'href="{default_href}"' not in body:
        return body
    hub_href = static(scitex_env(request)["SCITEX_FAVICON"])
    return body.replace(f'href="{default_href}"', f'href="{hub_href}"')


def _body_open_tag(body: str):
    """The real <body> tag; comments and head scripts in the shell spell out "<body>"."""
    start = body.find("</head>")
    comments = [m.span() for m in re.finditer(r"<!--.*?-->", body, re.S)]
    for match in re.finditer(r"<body\b[^>]*>", body[start:]):
        pos = start + match.start()
        if not any(a <= pos < b for a, b in comments):
            return re.compile(r"<body\b[^>]*>").match(body, pos)
    return None


def inject_frame_stylesheet(request, response) -> None:
    """Give a standalone leaf page the hub frame, header and themed ground."""
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

    link = (
        f'<link rel="stylesheet" href="{static(FRAME_STYLESHEET)}" />'
        f'<link rel="stylesheet" href="{static(LEAF_CHROME_STYLESHEET)}" />'
    )
    body = body[:head_end] + link + body[head_end:]
    body = _hub_favicon(request, body)
    header = _leaf_header(request, body)
    if header:
        body_open = _body_open_tag(body)
        if body_open:
            body = body[: body_open.end()] + header + body[body_open.end():]
    data = body.encode(charset)
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
        # The header render runs context processors that read request.user.
        await sync_to_async(self._safe_inject)(request, response)
        return response

    @staticmethod
    def _safe_inject(request, response):
        try:
            inject_frame_stylesheet(request, response)
        except Exception:
            # Layout polish must never break the page it decorates.
            logger.exception("[site-content-frame] injection failed for %s", request.path)


# EOF
