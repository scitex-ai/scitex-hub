#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``app list`` / ``app show-current`` / ``app show-info`` read verbs.

All three are read verbs per §2, so they expose ``--json``.
"""

from __future__ import annotations

import click

from .._flags import emit_json, json_flag
from ._group import app, console


@app.command("list")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default="http://127.0.0.1:8000",
    help="SciTeX Hub server URL",
)
@json_flag()
def app_list(server, json_output) -> None:
    """List available apps.

    \b
    Example:
        scitex-hub app list
        scitex-hub app list --json
        scitex-hub app list --server https://scitex.example.com
    """
    from scitex_hub.appmaker import list_all

    apps = list_all(server_url=server)

    if json_output:
        emit_json(apps or [])
        return

    if not apps:
        console.print("[yellow]No apps found.[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Apps")
    table.add_column("Name", style="cyan")
    table.add_column("Label")
    table.add_column("Order", justify="right")
    table.add_column("Description")

    for a in apps:
        table.add_row(
            a.get("name") or a.get("module_name", ""),
            a.get("label", ""),
            str(a.get("order", "")),
            (a.get("ai_hint") or a.get("short_description", ""))[:60],
        )

    console.print(table)


@app.command("show-current")
@json_flag()
def app_current(json_output) -> None:
    """Show the currently active app.

    \b
    Example:
        scitex-hub app show-current
        scitex-hub app show-current --json
    """
    from scitex_hub.appmaker import get_current

    name = get_current()
    if json_output:
        emit_json({"current": name})
        return
    if name:
        console.print(f"[cyan]{name}[/cyan]")
    else:
        console.print("[yellow]No active app (SCITEX_CURRENT_APP not set)[/yellow]")


@app.command("show-info")
@click.argument("app_name")
@json_flag()
def app_info(app_name, json_output) -> None:
    """Show detailed info for an app.

    \b
    Example:
        scitex-hub app show-info writer
        scitex-hub app show-info scholar --json
    """
    from scitex_hub.appmaker import get_info

    info = get_info(app_name)
    if not info:
        if json_output:
            emit_json({"error": "app not found", "app": app_name})
        else:
            console.print(f"[red]App not found:[/red] {app_name}")
        raise SystemExit(1)

    if json_output:
        emit_json(info)
        return

    for key, val in info.items():
        console.print(f"  [cyan]{key}:[/cyan] {val}")


# EOF
