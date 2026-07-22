#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/_sdk_common.py
"""SDK CLI shared helpers — JSON emission + the read-verb --json flag."""

import click

from ._flags import emit_json


def _maybe_emit(result, *, as_json: bool) -> None:
    """Render *result* either as pretty JSON or a one-line human summary.

    Default behaviour preserves the historical JSON output. The ``--no-json``
    branch prints a short summary so shell pipelines can opt into terse
    output without parsing JSON.
    """

    if as_json:
        emit_json(result)
        return
    if isinstance(result, list):
        click.echo(f"{len(result)} item(s)")
        return
    if isinstance(result, dict):
        keys = ", ".join(sorted(result)[:8])
        click.echo(f"dict[{len(result)} keys]: {keys}")
        return
    click.echo(str(result))


# Shared decorator for read verbs: --json defaults to True (historical).
_read_json = click.option(
    "--json/--no-json",
    "as_json",
    default=True,
    help="Output as JSON (default). Use --no-json for a short summary.",
)


# EOF
