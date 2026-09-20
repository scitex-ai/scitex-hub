#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``account whoami`` — polysemous-leaf identity check.

Per scitex-dev's convention doctrine (msg 548d1e6e), ``whoami`` uses
the polysemous-leaf escape from ``_skills/general/03_interface/02_cli/
02_subcommand-structure-noun-verb.md`` §"polysemous show-me-X".
"""

from __future__ import annotations

import json
import sys

import click
import requests

from ._group import account, console
from ._token import _read_cached_token, _resolve_server


@account.command("whoami")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default=None,
    help="SciTeX Hub server URL.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def whoami(server, as_json):
    """Print who the cached token authenticates as (username, id, plan, key).

    Same identity probe the demo's middleware-verification step used —
    handy for "is my token still valid?" without a separate health
    endpoint.

    \b
    Example:
        scitex-hub account whoami
        scitex-hub account whoami --json
        scitex-hub account whoami --server https://scitex.ai
    """
    server_url = _resolve_server(server)
    cached = _read_cached_token() or {}
    bearer = cached.get("access")
    if not bearer:
        console.error(
            "[red]No cached token.[/red] Run `scitex-hub account token create` first."
        )
        sys.exit(2)

    try:
        resp = requests.get(
            f"{server_url}/api/me/",
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=10,
        )
    except requests.ConnectionError:
        console.error(f"[red]Cannot reach {server_url}.[/red]")
        sys.exit(1)

    if resp.status_code == 401:
        console.error("[red]Token expired or invalid.[/red]")
        sys.exit(1)
    if resp.status_code != 200:
        console.error(f"[red]HTTP {resp.status_code}:[/red] {resp.text[:200]}")
        sys.exit(1)

    data = resp.json()
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
        return
    username = data.get("username", "?")
    plan = data.get("plan") or "(none)"
    expires_at = data.get("expires_at") or "never"
    console.info(f"username: [cyan]{username}[/cyan]")
    console.info(f"id:       [cyan]{data.get('id', '?')}[/cyan]")
    console.info(f"plan:     [cyan]{plan}[/cyan]")
    if data.get("key_id") is not None:
        console.info(f"key:      [cyan]#{data['key_id']} (expires {expires_at})[/cyan]")
    console.info(f"server:   [cyan]{server_url}[/cyan]")


# EOF
