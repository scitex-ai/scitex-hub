#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``account token create / list / revoke`` — CLI verbs over /api/me/token/.

Phase-1 PR-4 client-side counterparts of Phase-1 PR-3's endpoint
(see PR #273). Each verb talks HTTPS to the configured server URL +
caches/reads the token at the canonical
``~/.scitex/cloud/runtime/token.json`` location.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import requests

from ._group import console, token

#: Default scopes for a CLI-issued token. Mirrors
#: :data:`apps.infra.accounts_app.views.me_token_views.ALLOWED_CLI_SCOPES`
#: — the server-side allowlist is the source of truth; this default just
#: avoids the user having to type it on every call.
DEFAULT_CLI_SCOPES = ("publish",)


def _token_cache_path() -> Path:
    """Resolve the cached token location.

    Uses the same path the workspace JWT path uses
    (``scitex_config._ecosystem.local_state.runtime_path("cloud",
    "token.json")``) so any pre-existing cache from the JWT route stays
    valid for the new APIKey route too — both are just Bearer tokens
    from the CLI's perspective.
    """
    try:
        from scitex_config._ecosystem import local_state

        return local_state.runtime_path("cloud", "token.json")
    except Exception:
        # Fallback for non-scitex environments — keep the CLI usable.
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


def _resolve_server(server: str | None) -> str:
    """Normalise the server URL (strip trailing slash)."""
    if server:
        return server.rstrip("/")
    cached = _read_cached_token() or {}
    if cached.get("server"):
        return str(cached["server"]).rstrip("/")
    return "https://scitex.ai"


@token.command("create")
@click.option("--user", "-u", required=True, help="Your hub username.")
@click.option(
    "--password",
    "-p",
    prompt=True,
    hide_input=True,
    help="Your hub password (prompted if not given).",
)
@click.option(
    "--scope",
    "scopes",
    multiple=True,
    default=DEFAULT_CLI_SCOPES,
    show_default=True,
    help=(
        "Scope to request. Server enforces an allowlist; only "
        "`publish` is accepted for CLI-issued tokens today. Pass "
        "--scope multiple times for richer (future) sets."
    ),
)
@click.option(
    "--name",
    "-n",
    default="scitex-hub-cli",
    show_default=True,
    help="Human-readable name for the token (visible in the UI).",
)
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default=None,
    help="SciTeX Hub server URL. Defaults to cached token.json or scitex.ai.",
)
@click.option(
    "--save/--no-save",
    default=True,
    show_default=True,
    help="Cache the minted token to ~/.scitex/cloud/runtime/token.json.",
)
def token_create(user, password, scopes, name, server, save):
    """Mint a new ``scitex_xxxx`` API token from your username+password.

    Posts to ``/api/me/token/`` on the server. Server-side validates
    the scope allowlist (``{"publish"}`` today), rate-limits per-IP +
    per-username, and uses a constant-time error path so a wrong
    password is indistinguishable from an unknown user.

    \b
    Examples:
        scitex-hub account token create --user ywatanabe
        scitex-hub account token create -u ywatanabe -n "from-laptop"
    """
    server_url = _resolve_server(server)
    body = {
        "username": user,
        "password": password,
        "scopes": list(scopes),
        "name": name,
    }
    try:
        resp = requests.post(f"{server_url}/api/me/token/", json=body, timeout=20)
    except requests.ConnectionError:
        console.print(f"[red]Cannot reach {server_url}. Check --server.[/red]")
        sys.exit(1)

    if resp.status_code == 201:
        data = resp.json()
        token_value = data["token"]
        if save:
            p = _token_cache_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"server": server_url, "access": token_value}))
            p.chmod(0o600)
            console.print(
                f"[green]Token created.[/green] Cached at [cyan]{p}[/cyan] (mode 600)."
            )
            console.print(
                f"  prefix: [cyan]{data.get('prefix', '')}[/cyan]   "
                f"scopes: [cyan]{','.join(data.get('scopes', []))}[/cyan]"
            )
        else:
            # NOT --save → print to stdout so the user can route it
            # themselves (env var, secret manager, …). Print only the
            # raw token, no other text, so `$(scitex-hub account token
            # create … --no-save)` is captureable.
            click.echo(token_value)
        return

    if resp.status_code == 401:
        console.print("[red]Authentication failed.[/red] Wrong username or password.")
        sys.exit(1)
    if resp.status_code == 400:
        try:
            err = resp.json().get("error", resp.text)
        except ValueError:
            err = resp.text
        console.print(f"[red]Bad request:[/red] {err}")
        sys.exit(2)
    if resp.status_code == 429:
        console.print("[red]Too many attempts.[/red] Rate-limited; try again later.")
        sys.exit(1)
    console.print(
        f"[red]Unexpected response[/red] HTTP {resp.status_code}: {resp.text[:200]}"
    )
    sys.exit(1)


@token.command("list")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default=None,
    help="SciTeX Hub server URL.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a table.")
def token_list(server, as_json):
    """List your existing API tokens (never re-shows the secret value)."""
    server_url = _resolve_server(server)
    cached = _read_cached_token() or {}
    bearer = cached.get("access")
    if not bearer:
        console.print(
            "[red]No cached token.[/red] Run `scitex-hub account token create` first."
        )
        sys.exit(2)

    try:
        resp = requests.get(
            f"{server_url}/api/me/tokens/",
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=15,
        )
    except requests.ConnectionError:
        console.print(f"[red]Cannot reach {server_url}.[/red]")
        sys.exit(1)

    if resp.status_code != 200:
        console.print(f"[red]HTTP {resp.status_code}:[/red] {resp.text[:200]}")
        sys.exit(1)

    rows = resp.json().get("tokens", [])
    if as_json:
        click.echo(json.dumps(rows, indent=2, default=str))
        return

    if not rows:
        console.print("[yellow]No tokens.[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Account tokens")
    for col, style in (
        ("id", "cyan"),
        ("name", None),
        ("prefix", "cyan"),
        ("scopes", None),
        ("active", "green"),
        ("created", None),
        ("last_used", None),
    ):
        table.add_column(col, style=style)
    for row in rows:
        table.add_row(
            str(row.get("id", "")),
            str(row.get("name", "")),
            str(row.get("prefix", "")),
            ",".join(row.get("scopes", [])),
            "yes" if row.get("is_active") else "no",
            str(row.get("created_at", ""))[:19],
            str(row.get("last_used_at", "") or "")[:19],
        )
    console.print(table)


@token.command("revoke")
@click.argument("token_id", type=int)
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default=None,
    help="SciTeX Hub server URL.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Confirm destructive action (required for non-interactive use).",
)
def token_revoke(token_id, server, yes):
    """Revoke a single API token by id. Requires ``--yes``."""
    if not yes:
        console.print(
            f"[red]error[/red]: pass --yes/-y to confirm: revoke token id={token_id}"
        )
        sys.exit(2)

    server_url = _resolve_server(server)
    cached = _read_cached_token() or {}
    bearer = cached.get("access")
    if not bearer:
        console.print("[red]No cached token.[/red]")
        sys.exit(2)

    try:
        resp = requests.delete(
            f"{server_url}/api/me/token/{token_id}/",
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=15,
        )
    except requests.ConnectionError:
        console.print(f"[red]Cannot reach {server_url}.[/red]")
        sys.exit(1)

    if resp.status_code == 204:
        console.print(f"[green]Token id={token_id} revoked.[/green]")
        return
    if resp.status_code == 404:
        console.print(f"[red]Token id={token_id} not found.[/red]")
        sys.exit(1)
    console.print(f"[red]HTTP {resp.status_code}:[/red] {resp.text[:200]}")
    sys.exit(1)


# EOF
