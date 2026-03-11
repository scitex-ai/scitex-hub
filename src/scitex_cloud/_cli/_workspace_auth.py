#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/_workspace_auth.py
"""Workspace CLI - JWT authentication helpers."""

import json
import sys
from pathlib import Path

import click
import requests

# Cached token location
TOKEN_CACHE_PATH = Path.home() / ".config" / "scitex" / "token.json"


def get_server_url(server):
    """Normalise server URL — strip trailing slash."""
    return server.rstrip("/")


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


def get_jwt_token(server_url):
    """Return a valid JWT access token.

    Uses cached token when available; otherwise prompts for credentials
    and calls /api/token/ to obtain a fresh pair.
    """
    cached = load_cached_token(server_url)
    if cached:
        return cached

    click.echo(f"Authenticating with {server_url}")
    username = click.prompt("Username")
    password = click.prompt("Password", hide_input=True)

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
