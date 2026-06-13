#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/account/_auth.py
"""Shared bearer-token resolution for the account Python API.

The CLI (``src/scitex_hub/_cli/_account/_token.py``) caches a freshly
minted ``scitex_xxxx`` API token at
``~/.scitex/cloud/runtime/token.json`` (mode 0600). The Python API
mirrors that contract but ALSO honours ``SCITEX_HUB_TOKEN`` as the
canonical env-var override so CI / agent code can inject a token
without touching disk.

Resolution order (first match wins):

1. ``os.environ["SCITEX_HUB_TOKEN"]`` — explicit env-var override.
2. ``~/.scitex/cloud/runtime/token.json`` ``access`` field — same path
   the CLI ``account token create --save`` writes.

If neither is set we raise ``RuntimeError`` rather than silently
falling back to anonymous — the operator-12845 rule for the Python
API is "fail loud, never publish anonymously."
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _token_cache_path() -> Path:
    """Resolve the canonical cached-token path.

    Mirrors :func:`scitex_hub._cli._account._token._token_cache_path` —
    same precedence: scitex_config's ecosystem helper first, plain
    ``~/.scitex/cloud/runtime/token.json`` fallback for environments
    without scitex_config installed.
    """
    try:
        from scitex_config._ecosystem import local_state

        return local_state.runtime_path("cloud", "token.json")
    except Exception:
        return Path.home() / ".scitex" / "cloud" / "runtime" / "token.json"


def _read_cached_token() -> dict[str, Any] | None:
    """Return the cached token dict, or ``None`` if absent/unreadable."""
    p = _token_cache_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def resolve_bearer() -> str:
    """Resolve the bearer token for an authenticated request.

    Returns:
        The bearer-token string (without the ``Bearer `` prefix).

    Raises:
        RuntimeError: Neither ``SCITEX_HUB_TOKEN`` nor a cached
            ``token.json`` ``access`` field is set. Operator-12845
            policy: fail loud so the user knows to log in.
    """
    env_token = os.environ.get("SCITEX_HUB_TOKEN")
    if env_token:
        return env_token
    cached = _read_cached_token() or {}
    access = cached.get("access")
    if access:
        return str(access)
    raise RuntimeError("not logged in — run `scitex-hub auth login` first")


def resolve_server(server: str | None = None) -> str:
    """Resolve the server URL.

    Precedence:
      1. Explicit ``server`` argument (trailing-slash stripped).
      2. ``SCITEX_HUB_URL`` env var.
      3. ``server`` field from cached ``token.json``.
      4. ``https://scitex.ai`` default.
    """
    if server:
        return server.rstrip("/")
    env_url = os.environ.get("SCITEX_HUB_URL")
    if env_url:
        return env_url.rstrip("/")
    cached = _read_cached_token() or {}
    cached_server = cached.get("server")
    if cached_server:
        return str(cached_server).rstrip("/")
    return "https://scitex.ai"


# EOF
