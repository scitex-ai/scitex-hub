#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``app prefs`` sub-group: get / update / delete / list per-user app prefs."""

from __future__ import annotations

import json as _json

import click

from .._click_compat import (
    register_warn_alias,
    spec_command_kwargs,
    spec_group_kwargs,
)
from .._flags import (
    confirm_or_abort,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
)
from ._group import app, console


@app.group("prefs", **spec_group_kwargs(summary="Manage per-user app preferences."))
def app_prefs() -> None:
    """Manage per-user app preferences."""


@app_prefs.command(
    "get",
    **spec_command_kwargs(
        summary="Show preferences for an app.",
        examples=(("{prog} app prefs get writer", "Show prefs for one app."),),
    ),
)
@click.argument("app_name")
@json_flag()
def prefs_get(app_name, json_output) -> None:
    """Show preferences for an app.

    \b
    Example:
        scitex-hub app prefs get writer
        scitex-hub app prefs get writer --json
    """
    from scitex_hub.appmaker import get_prefs

    prefs = get_prefs(app_name)

    if json_output:
        emit_json(prefs or {})
        return

    if not prefs:
        console.print(f"[yellow]No preferences saved for {app_name}[/yellow]")
        return

    console.print(_json.dumps(prefs, indent=2))


@app_prefs.command(
    "update",
    **spec_command_kwargs(
        summary="Update preferences for an app as key=value pairs.",
        examples=(
            ("{prog} app prefs update writer theme=dark", "Update one pref."),
        ),
    ),
)
@click.argument("app_name")
@click.argument("key_values", nargs=-1)
def prefs_set(app_name, key_values) -> None:
    """Update preferences for an app as key=value pairs.

    \b
    Example:
        scitex-hub app prefs update writer theme=dark font_size=14
        scitex-hub app prefs update scholar engine=crossref
    """
    from scitex_hub.appmaker import set_prefs

    prefs: dict = {}
    for kv in key_values:
        if "=" not in kv:
            console.print(f"[red]Invalid format:[/red] {kv} (expected key=value)")
            raise SystemExit(1)
        key, val = kv.split("=", 1)
        try:
            prefs[key] = _json.loads(val)
        except (_json.JSONDecodeError, ValueError):
            prefs[key] = val

    set_prefs(app_name, prefs)
    console.print(f"[green]Saved preferences for {app_name}[/green]")


# §1f verb rename: `prefs set` -> `prefs update` (warn-phase alias).
register_warn_alias(app_prefs, "set", target="update", remove_in="0.20")


@app_prefs.command(
    "delete",
    **spec_command_kwargs(
        summary="Delete all preferences for an app.",
        examples=(("{prog} app prefs delete writer --yes", "Delete an app's prefs."),),
    ),
)
@click.argument("app_name")
@mutating_flags()
def prefs_delete(app_name, dry_run, yes) -> None:
    """Delete all preferences for an app.

    \b
    Example:
        scitex-hub app prefs delete writer
        scitex-hub app prefs delete writer --yes
    """
    if dry_run:
        print_dry_run(f"would delete all preferences for {app_name}")
        return

    confirm_or_abort(
        f"Delete all preferences for {app_name}?", yes=yes, dry_run=dry_run
    )

    from scitex_hub.appmaker import delete_prefs

    if delete_prefs(app_name):
        console.print(f"[green]Deleted preferences for {app_name}[/green]")
    else:
        console.print(f"[yellow]No preferences found for {app_name}[/yellow]")


@app_prefs.command(
    "list",
    **spec_command_kwargs(
        summary="List all saved app preferences.",
        examples=(("{prog} app prefs list", "List all prefs."),),
    ),
)
@json_flag()
def prefs_list(json_output) -> None:
    """List all saved app preferences.

    \b
    Example:
        scitex-hub app prefs list
        scitex-hub app prefs list --json
    """
    from scitex_hub.appmaker import list_prefs

    all_prefs = list_prefs()

    if json_output:
        emit_json(all_prefs or {})
        return

    if not all_prefs:
        console.print("[yellow]No preferences saved[/yellow]")
        return

    console.print(_json.dumps(all_prefs, indent=2))


# EOF
