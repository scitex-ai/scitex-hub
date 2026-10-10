"""FigRecipe Apptainer pilot: hub-side reverse proxy to the container.

Pilot slice (card hub-figrecipe-leaf-move-20261009): the hub keeps
EVERYTHING it owns — the ``login_required`` auth gate, project scoping,
the SITE-2 jail guard (``urls/figrecipe.py``), the bespoke
``apps/figrecipe/`` mount — and stops owning the editor HTML BYTES: when
the pilot is enabled, ``figure_editor`` returns the container-rendered
page instead of the hub-rendered leaf template.

Boundary contract (no shared sessions, no shared Django secret):

* Auth: per-request HMAC token minted by the LEAF's own
  ``figrecipe._django._container_auth`` (hub vendors no crypto), sent as
  ``X-FigRecipe-Auth``. Secret is ``FIGRECIPE_CONTAINER_AUTH_KEY`` (env
  only, Infra-provided). Missing secret disables the pilot (fail-safe).
* Transport: loopback HTTP to ``SCITEX_FIGRECIPE_CONTAINER_URL``
  (default disabled; pilot ``http://127.0.0.1:18096``). Cookies and
  ``Authorization`` are STRIPPED before forwarding; ``X-Forwarded-For`` /
  ``X-Forwarded-Proto`` are set. The browser never talks to the container.
* Failure: container unreachable → :class:`ContainerUnavailable`; the
  caller falls back to the in-process leaf render with a warning (pilot
  reversibility — same pattern as the leaf adapter's hub fallback).
* API DISPATCH IS NOT PROXIED THIS SLICE: ``api_dispatch_with_context``
  stays in-process behind the SITE-2 guard. The container's page points
  its SPA at the guarded hub wrapper (``stx_mount``), so every mutating
  call still passes the proven jail. The API flips only after the
  container proves containment + SAC-manager sign-off.
"""

from __future__ import annotations

import http.client
import logging
import os
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

TOKEN_HEADER = "X-FigRecipe-Auth"
URL_ENV = "SCITEX_FIGRECIPE_CONTAINER_URL"
KEY_ENV = "FIGRECIPE_CONTAINER_AUTH_KEY"
TIMEOUT_ENV = "SCITEX_FIGRECIPE_CONTAINER_TIMEOUT"
DEFAULT_TIMEOUT = 10

_HOP_HEADERS = {
    "cookie",
    "authorization",
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class ContainerUnavailable(Exception):
    """The container could not serve this request (down/timeout/protocol)."""


def enabled() -> bool:
    """True only when a URL AND a token secret are both configured."""
    return bool(os.environ.get(URL_ENV) and os.environ.get(KEY_ENV))


def _container_parts():
    parts = urlsplit(os.environ.get(URL_ENV, ""))
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ContainerUnavailable(f"Bad {URL_ENV}")
    return parts


def _target_for(request):
    """Return ``(scheme, host, port)`` for this request's user container.

    Per-user-UID model: mapped logins get loopback + per-uid port (their
    own instance, spawned as their uid); unmapped logins use the single
    configured URL (dev/test) — and fail closed when THAT is unset too.
    """
    parts = _container_parts()
    try:
        from .container_spawner import container_host_port
    except ImportError:
        return (parts.scheme, parts.hostname, parts.port or 80)
    try:
        host, port = container_host_port(request)
        return (parts.scheme, host, port)
    except Exception:
        # No uid map for this login (pilot allowlist): single-container
        # fallback so unmapped users keep the in-process-equivalent path.
        return (parts.scheme, parts.hostname, parts.port or 80)


def mint_token_for(request, current_project=None) -> str:
    """Mint the hub→container token via the leaf's own crypto module.

    Authority (user/project/root/write) is resolved read-only through the
    SDK provider — no writes, no navigation change. The leaf module owns
    the HMAC construction; the hub only supplies the resolved facts.
    """
    try:
        from figrecipe._django._container_auth import mint_token as _leaf_mint
    except ImportError as exc:
        raise ContainerUnavailable(f"Leaf container auth unavailable: {exc}") from exc
    try:
        from scitex_sdk.host import project_access as _sdk_access
    except ImportError as exc:
        raise ContainerUnavailable(f"SDK unavailable: {exc}") from exc

    write = request.method not in ("GET", "HEAD", "OPTIONS")
    access = _sdk_access(request, write=write, remember=False)
    user = getattr(request, "user", None)
    return _leaf_mint(
        user_id=str(getattr(user, "pk", "") or getattr(user, "username", "")),
        project_id=str(access.id),
        root=str(access.root),
        can_write=bool(access.can_write),
    )


def proxy_request(request, subpath: str = "", *, token: str | None = None):
    """Forward the current request to the container; return HttpResponse.

    ``subpath`` is the container-side path (``""`` = page root). Raises
    :class:`ContainerUnavailable` on any transport failure — the caller
    falls back to the in-process render.
    """
    from django.http import HttpResponse

    parts = _container_parts()
    scheme, host, port = _target_for(request)
    timeout = int(os.environ.get(TIMEOUT_ENV, DEFAULT_TIMEOUT))
    auth = token if token is not None else mint_token_for(request)
    target = "/" + (subpath or "").lstrip("/")
    if request.META.get("QUERY_STRING"):
        target += "?" + request.META["QUERY_STRING"]

    forward = {
        "X-FigRecipe-Auth": auth,
        "X-Forwarded-For": request.META.get("REMOTE_ADDR", ""),
        "X-Forwarded-Proto": "https" if request.is_secure() else "http",
    }
    content_type = request.META.get("CONTENT_TYPE", "")
    if content_type:
        forward["Content-Type"] = content_type
    # Pass through safe browser headers; strip cookies/auth/hop headers.
    for key, value in request.headers.items():
        if key.lower() in _HOP_HEADERS or key.lower().startswith("x-figrecipe-"):
            continue
        if key.lower() in ("accept", "accept-language", "user-agent", "referer"):
            forward[key] = value

    body = request.body or None
    host = host or ""
    default_port = 443 if scheme == "https" else 80
    try:
        if scheme == "https":
            conn = http.client.HTTPSConnection(host, port or default_port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port or default_port, timeout=timeout)
        try:
            conn.request(request.method, target, body=body, headers=forward)
            resp = conn.getresponse()
            payload = resp.read()
            response = HttpResponse(
                payload,
                status=resp.status,
                content_type=resp.getheader("Content-Type", "text/html"),
            )
            return response
        finally:
            conn.close()
    except Exception as exc:
        raise ContainerUnavailable(f"Container {host} unreachable: {exc}") from exc


def proxy_page(request, current_project=None):
    """Proxy the editor page (GET root). API stays hub-guarded this slice."""
    return proxy_request(request, "")
