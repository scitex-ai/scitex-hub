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
    """Print the username + email the cached token authenticates as.

    Same identity probe the demo's middleware-verification step used —
    handy for "is my token still valid?" without a separate health
    endpoint.
    """
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
            f"{server_url}/api/me/",
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=10,
        )
    except requests.ConnectionError:
        console.print(f"[red]Cannot reach {server_url}.[/red]")
        sys.exit(1)

    if resp.status_code == 401:
        console.print("[red]Token expired or invalid.[/red]")
        sys.exit(1)
    if resp.status_code != 200:
        console.print(f"[red]HTTP {resp.status_code}:[/red] {resp.text[:200]}")
        sys.exit(1)

    data = resp.json()
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
        return
    username = data.get("username", "?")
    email = data.get("email", "?")
    console.print(f"username: [cyan]{username}[/cyan]")
    console.print(f"email:    [cyan]{email}[/cyan]")
    console.print(f"server:   [cyan]{server_url}[/cyan]")


# EOF
