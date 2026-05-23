#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/_workspace_auth.py
"""Workspace CLI - JWT authentication helpers."""

import json
import os
import sys

import click
import requests
from scitex_config._ecosystem import local_state

from .._config import get_config_value

# Cached token location
TOKEN_CACHE_PATH = local_state.runtime_path("cloud", "token.json")


def get_server_url(server):
    """Normalise server URL — strip trailing slash."""
    return server.rstrip("/")


def _resolve_workspace_credentials():
    """Resolve (username, password) from env → config, per spec §6b.

    No interactive prompting: missing values are reported by the caller
    with exit code 2. CLI flag values (when the caller has them) take
    precedence over what this helper returns.
    """
    username = os.environ.get("SCITEX_CLOUD_WORKSPACE_USER") or get_config_value(
        "workspace", "user"
    )
    password = os.environ.get("SCITEX_CLOUD_WORKSPACE_PASSWORD") or get_config_value(
        "workspace", "password"
    )
    return username, password


def load_cached_token(server_url):
    """Return cached access token for server_url, or None if missing/stale."""
    if not TOKEN_CACHE_PATH.exists():
        return None
    try:
        cached = json.loads(TOKEN_CACHE_PATH.read_text())
        if cached.get("server") == server_url and cached.get("access"):
            return cached["access"]
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_token(server_url, tokens):
    """Persist JWT tokens to the local cache file."""
    TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_PATH.write_text(json.dumps({**tokens, "server": server_url}))


def get_jwt_token(server_url, username=None, password=None):
    """Return a valid JWT access token.

    Uses cached token when available; otherwise requires credentials
    from (in precedence order): function arguments (CLI flags) →
    ``SCITEX_CLOUD_WORKSPACE_USER`` / ``SCITEX_CLOUD_WORKSPACE_PASSWORD``
    env vars → config file (spec §6b). Missing credentials cause a
    fail-fast exit with code 2 — no interactive prompt, so this is
    safe to run under CI/agent/cron.
    """
    cached = load_cached_token(server_url)
    if cached:
        return cached

    env_user, env_password = _resolve_workspace_credentials()
    username = username or env_user
    password = password or env_password

    if not username or not password:
        click.echo(
            "error: workspace credentials missing. Set "
            "SCITEX_CLOUD_WORKSPACE_USER/SCITEX_CLOUD_WORKSPACE_PASSWORD, "
            "pass --user/--password, or configure "
            "~/.scitex/scitex-cloud/config.yaml",
            err=True,
        )
        sys.exit(2)

    click.echo(f"Authenticating with {server_url}", err=True)

    try:
        resp = requests.post(
            f"{server_url}/api/token/",
            json={"username": username, "password": password},
            timeout=15,
        )
    except requests.ConnectionError:
        click.echo(
            f"Error: Cannot connect to {server_url}. Is the server running?",
            err=True,
        )
        sys.exit(1)

    if resp.status_code != 200:
        click.echo(
            f"Error: Authentication failed (HTTP {resp.status_code}).",
            err=True,
        )
        click.echo(
            "Hint: Check credentials or use --server to specify the correct URL.",
            err=True,
        )
        sys.exit(1)

    tokens = resp.json()
    save_token(server_url, tokens)
    click.echo("Authentication successful. Token cached.")
    return tokens["access"]


def auth_headers(token):
    """Return authorization headers for JWT-authenticated requests."""
    return {"Authorization": f"Bearer {token}"}


def get_current_username(server_url, token):
    """Resolve the authenticated username via the Django /api/me/ endpoint."""
    try:
        resp = requests.get(
            f"{server_url}/api/me/",
            headers=auth_headers(token),
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("username")
    except requests.RequestException:
        pass
    return None


def require_username(server_url, token):
    """Return authenticated username or exit with a clear error."""
    username = get_current_username(server_url, token)
    if not username:
        click.echo(
            "Error: Could not determine your username from the server.", err=True
        )
        click.echo(
            "Hint: The server may not expose /api/me/. Check --server.", err=True
        )
        sys.exit(1)
    return username


# EOF
