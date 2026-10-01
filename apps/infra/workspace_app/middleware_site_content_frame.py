#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give mounted leaf-app pages the same desktop content frame as hub pages.

Hub pages load ``site-content-frame.css`` from ``global_head_styles.html``.
Standalone-shell pages load no hub template at all, so this middleware adds
the stylesheet links before ``</head>`` of those documents, swaps the tab
icon to the hub's, and prepends the real hub global header
(``global_header.html``) to ``<body>`` — the same header hub pages render,
not a title-only substitute.
"""

from __future__ import annotations

import logging
import re

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

logger = logging.getLogger(__name__)

FRAME_STYLESHEET = "shared/css/layouts/site-content-frame.css"
LEAF_CHROME_STYLESHEET = "shared/css/layouts/leaf-host-chrome.css"
LEAF_DEFAULT_FAVICON = "scitex_sdk/ui/img/scitex-favicon.svg"
# Font Awesome ships from CDN on hub pages (global_head_styles.html); the
# standalone shell brings none, and the header's hamburger/menu icons need it.
FONT_AWESOME_HREF = (
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
)
FONT_AWESOME_INTEGRITY = (
    "sha512-9usAa10IRO0HhonpyAIVpjrylPvoDwiPUiKdWk5t3PyolY1cOd4DSE0Ga+ri4AuTroPR5aQvXU9xC6qOPnzFeg=="  # pragma: allowlist secret
)
STANDALONE_SHELL_MARKER ='id="workspace-three-col"'
# Marker of the hub header this middleware injects: the hamburger button is
# unique to global_header.html, so its presence screens a second injection.
LEAF_HEADER_MARKER = 'id="mobile-hamburger-btn"'
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
    """The real hub global header for a leaf page, or "" when the page brings its own."""
    if request.GET.get("embed") == "1" or LEAF_HEADER_MARKER in body:
        return ""
    if any(marker in body for marker in OWN_HEADER_MARKERS):
        return ""
    from django.template.loader import render_to_string

    try:
        # Selective context, NOT request=request: a full RequestContext would
        # run EVERY context processor, including DB-hitting ones
        # (project_context resolves /<user>/<slug>/ via Project.objects),
        # which unit tests forbid and leaf loads should never pay for. The
        # header template only reads the keys built below — user, request,
        # CSRF, env/version branding and the logo target — all DB-free, the
        # same values hub pages receive from their own processors. This names
        # no leaf view: it is hub's own shared header rendered onto a
        # generic standalone shell.
        from django.middleware.csrf import get_token

        from config.context_processors import (
            debug_mode,
            header_logo,
            scitex_env,
            scitex_version,
        )

        context = {
            "user": getattr(request, "user", None),
            "request": request,
            "csrf_token": get_token(request),
            **debug_mode(request),
            **scitex_env(request),
            **scitex_version(request),
            **header_logo(request),
        }
        header = render_to_string("global_base_partials/global_header.html", context)
    except Exception:
        logger.exception("[site-content-frame] leaf header failed for %s", request.path)
        return ""
    # The standalone shell never loads the hub JS bundles, so the
    # command-palette search (shared/components/search.ts) has no wiring
    # here. A live button would be a lie: disable the triggers honestly and
    # say so in the markup. The hamburger keeps working — its fail-safe
    # wiring is inline in global_header/hamburger_inline.html and arrives
    # with the header itself.
    header = header.replace(
        "data-search-open", 'data-search-open disabled aria-disabled="true"'
    )
    return (
        "<!-- leaf-hosted hub header: search needs the hub JS bundle, "
        "so its triggers are disabled; the hamburger menu is inline-wired "
        "and works -->\n" + header
    )


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
    if "font-awesome" not in body and "fontawesome" not in body:
        link += (
            '<link rel="stylesheet" '
            f'href="{FONT_AWESOME_HREF}" '
            f'integrity="{FONT_AWESOME_INTEGRITY}" '
            'crossorigin="visitor" referrerpolicy="no-referrer" />'
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
