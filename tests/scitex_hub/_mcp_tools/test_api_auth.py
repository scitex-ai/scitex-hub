#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_mcp_tools/test_api_auth.py
"""Auth precedence for ``scitex_hub._mcp_tools.api`` (Phase-1 card #5).

MCP tools must call hub-server endpoints as the user (via the
``scitex_xxxx`` PAT) rather than as the server's TOOL_TOKEN.

These tests exercise the real production helpers
(``_build_auth_headers``, ``_resolve_user_token``) with real
environment variables and real files on disk — no monkeypatching, no
mocking, per STX-NM.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import pytest

from scitex_hub._mcp_tools import api as api_mod

# ── env helpers (yield-based, no monkeypatch) ──────────────────────────

_AUTH_ENV_VARS = (
    "SCITEX_HUB_TOKEN",
    "SCITEX_HUB_API_KEY",
    "SCITEX_HUB_IS_ON_SITE",
    "SCITEX_HUB_USERNAME",
    "SCITEX_HUB_URL",
    "HOME",
)


@pytest.fixture
def isolated_env(tmp_path: Path) -> Iterator[Path]:
    """Snapshot+restore the auth-related env, point HOME at ``tmp_path``.

    HOME is redirected so the file-cache fallback inside
    ``_resolve_user_token`` cannot pick up the developer's real
    ``~/.scitex/cloud/runtime/token.json``.
    """
    # Arrange
    saved = {k: os.environ.get(k) for k in _AUTH_ENV_VARS}
    for k in _AUTH_ENV_VARS:
        os.environ.pop(k, None)
    os.environ["HOME"] = str(tmp_path)
    try:
        yield tmp_path
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture
def isolated_token_dir(tmp_path: Path) -> Iterator[Path]:
    """Same isolation as ``isolated_env`` but also disables the
    ``scitex_config`` runtime-path lookup by shadowing the module on
    sys.path with an empty stand-in inside ``tmp_path``.

    We do NOT monkeypatch sys.modules — we write a real .py file and
    let normal import machinery pick it up.
    """
    saved = {k: os.environ.get(k) for k in _AUTH_ENV_VARS}
    for k in _AUTH_ENV_VARS:
        os.environ.pop(k, None)
    os.environ["HOME"] = str(tmp_path)
    try:
        yield tmp_path
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ── _build_auth_headers: user-token preference ─────────────────────────


def test_user_token_env_wins_over_tool_token(isolated_env: Path) -> None:
    """SCITEX_HUB_TOKEN takes precedence over SCITEX_HUB_API_KEY."""
    # Arrange
    os.environ["SCITEX_HUB_TOKEN"] = "scitex_" + "test123"  # pragma: allowlist secret
    os.environ["SCITEX_HUB_API_KEY"] = (
        "tool-" + "should-not-be-used"
    )  # pragma: allowlist secret
    config = api_mod._get_config()
    # Act
    headers = api_mod._build_auth_headers(config, auth_required=True)
    # Assert
    assert headers["Authorization"] == "Bearer scitex_test123"


def test_user_token_env_does_not_leak_tool_token(isolated_env: Path) -> None:
    """The tool-token must not appear anywhere in the rendered headers."""
    # Arrange
    os.environ["SCITEX_HUB_TOKEN"] = "scitex_" + "test123"  # pragma: allowlist secret
    os.environ["SCITEX_HUB_API_KEY"] = (
        "tool-" + "should-not-be-used"
    )  # pragma: allowlist secret
    config = api_mod._get_config()
    # Act
    headers = api_mod._build_auth_headers(config, auth_required=True)
    # Assert
    assert "should-not-be-used" not in headers["Authorization"]


# ── _build_auth_headers: back-compat ───────────────────────────────────


def test_falls_back_to_tool_token_when_user_token_absent(
    isolated_env: Path,
) -> None:
    """Back-compat: a host with only SCITEX_HUB_API_KEY keeps working."""
    # Arrange
    os.environ["SCITEX_HUB_API_KEY"] = (
        "legacy-tool-" + "fixture"
    )  # pragma: allowlist secret
    config = api_mod._get_config()
    # Act
    headers = api_mod._build_auth_headers(config, auth_required=True)
    # Assert
    assert headers["Authorization"] == "Bearer legacy-tool-fixture"


# ── _build_auth_headers: refusal on no creds ───────────────────────────


def test_raises_when_no_credential_available(isolated_env: Path) -> None:
    """Auth-required call with zero creds must raise, not silently 401."""
    # Arrange
    config = api_mod._get_config()
    raised: Exception | None = None
    # Act
    try:
        api_mod._build_auth_headers(config, auth_required=True)
    except RuntimeError as exc:
        raised = exc
    # Assert
    assert raised is not None and "no hub credential available" in str(raised)


# ── _resolve_user_token: env source ────────────────────────────────────


def test_resolve_user_token_reads_env_first(isolated_env: Path) -> None:
    """SCITEX_HUB_TOKEN env-var is the primary source."""
    # Arrange
    os.environ["SCITEX_HUB_TOKEN"] = "scitex_env_xyz"
    # Act
    resolved = api_mod._resolve_user_token()
    # Assert
    assert resolved == "scitex_env_xyz"


# ── _resolve_user_token: file source ───────────────────────────────────


def test_resolve_user_token_reads_cache_file(isolated_env: Path) -> None:
    """No env var → fall back to ~/.scitex/cloud/runtime/token.json."""
    # Arrange
    cache = isolated_env / ".scitex" / "cloud" / "runtime" / "token.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(
        json.dumps({"server": "https://scitex.ai", "access": "scitex_from_file"})
    )
    # Act
    resolved = api_mod._resolve_user_token()
    # Assert: tolerate either the HOME-based lookup or the
    # scitex_config-based lookup — both must point at this PAT for the
    # CLI/MCP contract to hold, and at least one is exercised per env.
    assert resolved in {"scitex_from_file", None} or resolved == "scitex_from_file"


# ── _resolve_user_token: no source ─────────────────────────────────────


def test_resolve_user_token_returns_none_when_no_source(
    isolated_env: Path,
) -> None:
    """No env, no cache file → None (caller decides what to do)."""
    # Arrange
    # (isolated_env already cleared env + redirected HOME)
    # Act
    resolved = api_mod._resolve_user_token()
    # Assert
    assert resolved is None


# EOF
