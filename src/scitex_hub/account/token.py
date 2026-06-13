#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/account/token.py
"""Python parity for ``scitex-hub account token {create,list,revoke}``.

Each function thin-wraps the corresponding ``/api/me/...`` HTTP
endpoint that PR #273 / #274 wired up server-side. The transport is
the stdlib ``requests`` library — same as the CLI in
``src/scitex_hub/_cli/_account/_token.py`` — so behaviour matches the
shell-out path 1:1.

Authentication uses :func:`scitex_hub.account._auth.resolve_bearer`,
which fails loud (``RuntimeError``) if no token is available rather
than silently anonymising the call.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from ._auth import resolve_bearer, resolve_server

#: Default scopes for a CLI/API-issued token. Mirrors the server-side
#: ``ALLOWED_CLI_SCOPES`` allowlist on
#: ``apps.infra.accounts_app.views.me_token_views``.
DEFAULT_SCOPES: tuple[str, ...] = ("publish",)


def create(
    name: str = "scitex-hub-api",
    scopes: Sequence[str] | None = None,
    *,
    user: str | None = None,
    password: str | None = None,
    server: str | None = None,
    request_fn=None,
) -> dict:
    """Mint a new ``scitex_xxxx`` API token.

    POSTs to ``/api/me/token/``. Server-side validates the scope
    allowlist (currently ``{"publish"}``), rate-limits per-IP +
    per-username, and uses a constant-time error path so a wrong
    password is indistinguishable from an unknown user.

    Args:
        name: Human-readable name for the token (visible in the UI).
            Defaults to ``"scitex-hub-api"`` so the agent-programmatic
            path is visually distinct from the CLI default
            (``"scitex-hub-cli"``).
        scopes: Iterable of scope strings. Defaults to
            :data:`DEFAULT_SCOPES`.
        user: Username for basic-auth minting. Required when calling
            ``create()`` without an existing cached bearer token (the
            normal first-time login flow).
        password: Password for basic-auth minting. Required alongside
            ``user``.
        server: Override server URL. Defaults to
            :func:`._auth.resolve_server` (env / cache / scitex.ai).
        request_fn: Dependency-injection seam for the HTTP transport.
            When ``None``, uses ``requests.post`` directly. Tests pass
            a hand-rolled fake (see ``tests/scitex_hub/account/``).

    Returns:
        Dict with ``token``, ``prefix``, ``scopes``, and ``name``.

    Raises:
        ValueError: ``user``/``password`` missing (no other auth path).
        RuntimeError: Server rejected the request (bad creds, scope
            not allowlisted, rate limit, etc.).

    Example:
        >>> from scitex_hub.account import token
        >>> token.create(name="ci", scopes=["publish"],
        ...              user="ywatanabe", password="...")
        {'token': 'scitex_...', 'prefix': '...',
         'scopes': ['publish'], 'name': 'ci'}
    """
    if user is None or password is None:
        raise ValueError(
            "token.create requires user= and password= "
            "(basic-auth path — bearer-only minting is not supported)"
        )
    # NOTE: cannot use the ``list`` builtin here — we expose ``list``
    # as a module-level alias for :func:`list_` (CLI-verb mirror), and
    # that alias shadows the builtin inside this module. Use literal
    # unpacking instead.
    scope_list = [*scopes] if scopes is not None else [*DEFAULT_SCOPES]
    server_url = resolve_server(server)
    body = {
        "username": user,
        "password": password,
        "scopes": scope_list,
        "name": name,
    }
    do_request = request_fn if request_fn is not None else _default_post
    resp = do_request(f"{server_url}/api/me/token/", body)
    return _handle_create_response(resp)


def list_() -> list[dict]:
    """List existing API tokens (never re-shows the secret value).

    GETs ``/api/me/tokens/`` with the cached bearer token. Useful for
    answering "is my CI token still active?" without re-minting.

    Returns:
        List of token-metadata dicts. Each row carries ``id``,
        ``name``, ``prefix``, ``scopes``, ``is_active``,
        ``created_at``, and ``last_used_at`` — but never the secret
        token itself (only ``create`` ever returns the secret).

    Raises:
        RuntimeError: No bearer token resolved
            (:func:`._auth.resolve_bearer`) or server returned non-200.

    Example:
        >>> from scitex_hub.account import token
        >>> token.list_()
        [{'id': 1, 'name': 'cli', 'prefix': 'scitex_abcd',
          'scopes': ['publish'], 'is_active': True, ...}]
    """
    bearer = resolve_bearer()
    server_url = resolve_server()
    resp = _default_get(
        f"{server_url}/api/me/tokens/",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    if resp["status_code"] != 200:
        raise RuntimeError(f"HTTP {resp['status_code']}: {resp['text'][:200]}")
    # ``list`` builtin is shadowed by the module-level alias; literal-unpack instead.
    return [*resp["json"].get("tokens", [])]


# Public alias — `list` is a builtin so we expose both names. Callers
# can write either ``token.list()`` or ``token.list_()``. The trailing
# underscore is conventional PEP-8 for builtin-shadowing avoidance,
# the no-underscore form matches the literal CLI verb name.
list = list_  # noqa: A001  — intentional CLI-verb mirror; see docstring


def revoke(token_id: int) -> dict:
    """Revoke a single API token by id.

    DELETEs ``/api/me/token/{token_id}/``. Server responds 204 on
    success or 404 if the token doesn't belong to this user.

    Args:
        token_id: Server-assigned integer id (from
            :func:`list_`).

    Returns:
        Dict ``{"success": True, "token_id": <id>}`` on success.

    Raises:
        RuntimeError: No bearer token resolved, token not found
            (404), or any other non-204 response.

    Example:
        >>> from scitex_hub.account import token
        >>> token.revoke(7)
        {'success': True, 'token_id': 7}
    """
    bearer = resolve_bearer()
    server_url = resolve_server()
    resp = _default_delete(
        f"{server_url}/api/me/token/{token_id}/",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    if resp["status_code"] == 204:
        return {"success": True, "token_id": token_id}
    if resp["status_code"] == 404:
        raise RuntimeError(f"Token id={token_id} not found")
    raise RuntimeError(f"HTTP {resp['status_code']}: {resp['text'][:200]}")


def _handle_create_response(resp: dict) -> dict:
    """Normalise the ``/api/me/token/`` response into a plain dict."""
    status = resp["status_code"]
    if status == 201:
        return dict(resp["json"])
    if status == 401:
        raise RuntimeError("Authentication failed: wrong username or password")
    if status == 400:
        try:
            err = resp["json"].get("error", resp["text"])
        except (AttributeError, KeyError):
            err = resp["text"]
        raise RuntimeError(f"Bad request: {err}")
    if status == 429:
        raise RuntimeError("Too many attempts: rate-limited; try again later")
    raise RuntimeError(f"Unexpected response HTTP {status}: {resp['text'][:200]}")


def _default_post(url: str, body: dict) -> dict:
    """Default POST transport (used when no ``request_fn`` is injected).

    Wraps the response in a plain dict so the same shape works for
    real HTTP and for the hand-rolled test fakes — no ``requests``
    object leaks across the boundary.
    """
    import requests

    r = requests.post(url, json=body, timeout=20)
    return _wrap(r)


def _default_get(url: str, headers: dict) -> dict:
    import requests

    r = requests.get(url, headers=headers, timeout=15)
    return _wrap(r)


def _default_delete(url: str, headers: dict) -> dict:
    import requests

    r = requests.delete(url, headers=headers, timeout=15)
    return _wrap(r)


def _wrap(r) -> dict:
    """Turn a ``requests.Response`` into a dict the handlers expect."""
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
