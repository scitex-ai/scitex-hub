#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``account doctor`` — cached-credential health check.

Per scitex-dev's convention doctrine (msg 548d1e6e), ``doctor`` uses
the §1b single-token-verb exception for "is my cached creds healthy?"
diagnostics. Mirrors the pattern of ``scitex check-doctor``-style
introspection verbs elsewhere in the ecosystem.
"""

from __future__ import annotations

import sys

import click
import requests

from ._group import account, console
from ._token import _read_cached_token, _resolve_server, _token_cache_path


@account.command("doctor")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default=None,
    help="SciTeX Hub server URL.",
)
def doctor(server):
    """Report cached-token presence, file mode, and server reachability.

    \b
    Checks (in order):
      - token.json exists at the canonical path
      - file is readable + parses as JSON
      - mode is 600 (no group/other access)
      - "server" + "access" keys are present
      - GET /api/me/ with the cached Bearer returns 200

    Exits non-zero if any HARD check fails (missing file, bad JSON,
    missing keys, 401). World-readable file is a WARN, not a fail.
    """
    p = _token_cache_path()
    hard_fail = False
    console.print(f"[bold]token.json:[/bold] {p}")

    if not p.exists():
        console.print("  [red]✗[/red] does not exist")
        sys.exit(1)
    console.print("  [green]✓[/green] exists")

    mode = p.stat().st_mode & 0o777
    if mode == 0o600:
        console.print(f"  [green]✓[/green] mode 0o{mode:o}")
    else:
        console.print(f"  [yellow]![/yellow] mode 0o{mode:o} (recommended: 0o600)")

    cached = _read_cached_token()
    if cached is None:
        console.print("  [red]✗[/red] unreadable / invalid JSON")
        sys.exit(1)
    console.print("  [green]✓[/green] parses as JSON")

    if "server" not in cached or "access" not in cached:
        console.print("  [red]✗[/red] missing 'server' or 'access' key")
        sys.exit(1)
    console.print(
        f"  [green]✓[/green] server={cached['server']} "
        f"access=<{len(cached.get('access', ''))} chars>"
    )

    # Live probe
    server_url = _resolve_server(server)
    bearer = cached["access"]
    try:
        resp = requests.get(
            f"{server_url}/api/me/",
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=10,
        )
    except requests.ConnectionError:
        console.print(f"  [red]✗[/red] cannot reach {server_url}")
        sys.exit(1)

    if resp.status_code == 200:
        username = resp.json().get("username", "?")
        console.print(f"  [green]✓[/green] /api/me/ → 200 as [cyan]{username}[/cyan]")
    elif resp.status_code == 401:
        console.print("  [red]✗[/red] /api/me/ → 401 (token expired/invalid)")
        hard_fail = True
    else:
        console.print(f"  [red]✗[/red] /api/me/ → HTTP {resp.status_code}")
        hard_fail = True

    if hard_fail:
        sys.exit(1)
    console.print("[green]All checks passed.[/green]")


# EOF
