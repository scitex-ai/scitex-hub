#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``auth login`` — browser-free PAT mint + cache.

Phase-1 PR-5 / card #2 of lead's 7-card backlog. Thin shell over PR #273's
``POST /api/me/token/`` mint endpoint; the heavy lifting (allowlist,
per-IP/per-user rate limit, constant-time error path) lives server-side.

The verb takes ``--user`` and ``--password`` as options (§2: never
prompts — a missing option is a hard error, exit 2), posts them to
``/api/me/token/``, persists the returned ``scitex_xxxx``
PAT to the SAME canonical cache that ``scitex-hub account token *``
uses so subsequent CLI calls (whoami / doctor / publish) pick it up
automatically with zero extra config.

Per AGPL-3.0 SciTeX rules:
  - No silent fallback — every server error surfaces with URL + status.
  - The cache file is chmod-ed to ``0600`` after write.
  - On network error or 5xx, we raise loud with the URL + status code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import requests

from .._account._token import _read_cached_token, _resolve_server, _token_cache_path
from .._click_compat import spec_command_kwargs
from ._group import auth, console


def _post_mint(
    server_url: str,
    username: str,
    password: str,
    scopes: tuple[str, ...],
    name: str,
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """POST credentials to ``/api/me/token/`` and return the JSON body.

    Pulled out as a pure helper so the CLI test can exercise the HTTP
    contract with a hand-rolled fake transport (no ``unittest.mock`` per
    STX-NM repo rule; see ``tests/scitex_hub/_cli/_auth/test_login.py``).

    Raises :class:`requests.HTTPError` (with the response attached) on
    any non-201 — the caller is responsible for status-specific UX.
    The connection-layer ``requests.ConnectionError`` / ``Timeout`` are
    NOT caught here — they bubble up so the CLI layer can render them
    with the server URL in the message (AGPL-3.0 SciTeX "no silent
    fallback" rule).
    """
    body = {
        "username": username,
        "password": password,
        "scopes": list(scopes),
        "name": name,
    }
    http = session or requests
    resp = http.post(f"{server_url}/api/me/token/", json=body, timeout=timeout)
    if resp.status_code != 201:
        # Re-use requests' HTTPError so the call-site can switch on
        # ``err.response.status_code`` without parsing strings.
        raise requests.HTTPError(
            f"{resp.status_code} from {server_url}/api/me/token/",
            response=resp,
        )
    return resp.json()


def _persist_token(server_url: str, token_value: str) -> Path:
    """Write the minted PAT to the canonical cache (0600) and return path.

    Matches ``_account/_token.py``'s cache layout key-for-key so the
    rest of the CLI (whoami / doctor / publish) reads it transparently.
    """
    p = _token_cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"server": server_url, "access": token_value}))
    p.chmod(0o600)
    return p


# Default scopes — mirrors ``_account/_token.DEFAULT_CLI_SCOPES``. We
# don't import that constant because it's intentionally private to the
# ``_account`` subtree; duplicating one tuple is cheaper than coupling
# the auth verb to an internal name.
DEFAULT_LOGIN_SCOPES: tuple[str, ...] = ("publish",)


@auth.command(
    "login",
    **spec_command_kwargs(
        summary="Browser-free login: mint a PAT and cache it (mode 0600).",
        examples=(
            (
                "{prog} auth login --user alice --password '...'",
                "Mint + cache a PAT.",
            ),
        ),
    ),
)
@click.option(
    "--user",
    "-u",
    "username",
    default=None,
    help="Your hub username (required; never prompted).",
)
@click.option(
    "--password",
    "-p",
    default=None,
    help="Your hub password (required; never prompted).",
)
@click.option(
    "--scope",
    "scopes",
    multiple=True,
    default=DEFAULT_LOGIN_SCOPES,
    show_default=True,
    help="Scope to request. Server enforces an allowlist (today only 'publish').",
)
@click.option(
    "--name",
    "-n",
    default="scitex-hub-cli-login",
    show_default=True,
    help="Human-readable token name (visible in UI ``/account/tokens/``).",
)
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default=None,
    help="SciTeX Hub server URL. Defaults to cached token's server or scitex.ai.",
)
def auth_login(username, password, scopes, name, server):
    """Browser-free login — mint a PAT and cache it 0600.

    Takes username + password as options (never prompts), POSTs them to
    ``/api/me/token/`` (PR #273), persists the returned PAT to
    ``~/.scitex/cloud/runtime/token.json`` (mode 0600), and prints a
    confirmation line + a hint to export ``$SCITEX_HUB_TOKEN`` for
    sibling tools that prefer env-var auth.

    \b
    Examples:
        scitex-hub auth login -u ywatanabe -p '...'
        scitex-hub auth login -u ywatanabe -p '...' -s https://staging.scitex.ai
    """
    server_url = _resolve_server(server)

    # §2: never prompt — a missing credential option is a hard error.
    if not username:
        console.print(
            "[red]error[/red]: --user/-u is required "
            "(interactive prompts are not supported)."
        )
        sys.exit(2)
    if not password:
        console.print(
            "[red]error[/red]: --password/-p is required "
            "(interactive prompts are not supported)."
        )
        sys.exit(2)

    try:
        data = _post_mint(server_url, username, password, tuple(scopes), name)
    except requests.ConnectionError as exc:
        # AGPL-3.0 "no silent fallback": surface URL + cause.
        console.print(f"[red]Cannot reach[/red] [cyan]{server_url}[/cyan]: {exc}")
        sys.exit(1)
    except requests.Timeout as exc:
        console.print(f"[red]Timeout talking to[/red] [cyan]{server_url}[/cyan]: {exc}")
        sys.exit(1)
    except requests.HTTPError as exc:
        resp = exc.response
        status = resp.status_code if resp is not None else "???"
        if status == 401:
            console.print(
                "[red]Authentication failed.[/red] Wrong username or password."
            )
            sys.exit(1)
        if status == 400:
            try:
                err = resp.json().get("error", resp.text)
            except ValueError:
                err = resp.text if resp is not None else ""
            console.print(f"[red]Bad request[/red] from {server_url}: {err}")
            sys.exit(2)
        if status == 429:
            console.print(
                f"[red]Rate-limited[/red] by {server_url}. Try again shortly."
            )
            sys.exit(1)
        # 5xx and anything unexpected — loud surface per AGPL-3.0 rule.
        body = resp.text[:200] if resp is not None else ""
        console.print(
            f"[red]Unexpected response[/red] HTTP {status} from "
            f"[cyan]{server_url}/api/me/token/[/cyan]: {body}"
        )
        sys.exit(1)

    token_value = data["token"]
    cache_path = _persist_token(server_url, token_value)

    # Success UX — confirm identity, point at storage, give env-var hint.
    console.print(f"[green]logged in as[/green] [cyan]{username}[/cyan]")
    console.print(f"  token cached at [cyan]{cache_path}[/cyan] (mode 0600)")
    prefix = data.get("prefix", "")
    if prefix:
        console.print(
            f"  prefix: [cyan]{prefix}[/cyan]   "
            f"scopes: [cyan]{','.join(data.get('scopes', []))}[/cyan]"
        )
    console.print(
        "  hint: export [cyan]SCITEX_HUB_TOKEN[/cyan]=$(cat "
        f"{cache_path} | python -c 'import json,sys;"
        'print(json.load(sys.stdin)["access"])\')'
    )


# EOF
