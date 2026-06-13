#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/account/whoami.py
"""Python parity for ``scitex-hub account whoami``.

Same identity probe the CLI ``whoami`` verb hits — ``GET /api/me/`` —
so an agent-programmatic caller can confirm "is my cached token still
valid?" without shelling out.
"""

from __future__ import annotations

from ._auth import resolve_bearer, resolve_server


def whoami(*, server: str | None = None, request_fn=None) -> dict:
    """Return the username + email the cached bearer authenticates as.

    Args:
        server: Override server URL. Defaults to
            :func:`._auth.resolve_server` (env / cache / scitex.ai).
        request_fn: Dependency-injection seam for the HTTP GET. When
            ``None``, uses ``requests.get``. Tests inject a fake that
            returns the same ``{status_code, json, text}`` dict shape
            the real transport produces.

    Returns:
        Dict with at least ``username`` and ``email`` (server may add
        more fields like ``id`` or ``is_staff``).

    Raises:
        RuntimeError: No bearer token resolved (not logged in), token
            expired (401), or server returned non-200.

    Example:
        >>> from scitex_hub.account.whoami import whoami
        >>> whoami()
        {'username': 'ywatanabe', 'email': 'ywatanabe@scitex.ai'}
    """
    bearer = resolve_bearer()
    server_url = resolve_server(server)
    do_request = request_fn if request_fn is not None else _default_get
    resp = do_request(
        f"{server_url}/api/me/",
        {"Authorization": f"Bearer {bearer}"},
    )
    status = resp["status_code"]
    if status == 401:
        raise RuntimeError("Token expired or invalid")
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {resp['text'][:200]}")
    return dict(resp["json"])


def _default_get(url: str, headers: dict) -> dict:
    """Default GET transport — wraps ``requests`` into the dict shape."""
    import requests

    r = requests.get(url, headers=headers, timeout=10)
    try:
        body = r.json()
    except Exception:
        body = {}
    return {
        "status_code": r.status_code,
        "json": body,
        "text": r.text,
    }


# EOF
