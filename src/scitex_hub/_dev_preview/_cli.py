#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_cli.py

"""``scitex-hub dev-preview`` — the click surface over :mod:`._sync`.

The periodic job (:mod:`scitex_hub._jobs`) runs exactly
``scitex-hub dev-preview sync --clone /home/ywatanabe/proj/scitex-cloud``;
an operator runs the same verb by hand (``--dry-run`` first) to see what a
tick would do. Output is ALWAYS the outcome JSON on stdout — the
supervisor discards stdout anyway and a human reads ``sync.log``, so there
is no second, prettier format to drift from the first; ``--json`` is
accepted for the universal-flag contract. On a non-zero exit one human line
goes to stderr as well, because that is the only stream scitex-dev 0.59.0
keeps a tail of on failure.

No Django import anywhere on this path: the verb runs in the supervisor's
venv, not in the container.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from scitex_hub._cli._click_compat import spec_group_kwargs

from ._cards import CliCardFiler, NullCardFiler
from ._state import append_log
from ._sync import Config, sync

__all__ = ["dev_preview"]

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
_DEFAULT_STATE_DIR = Path.home() / ".scitex" / "hub" / "runtime" / "dev-preview-sync"


@click.group(
    "dev-preview",
    context_settings=_CONTEXT_SETTINGS,
    **spec_group_kwargs(
        summary="Keep the develop preview current.",
        description=(
            "Fast-forward the preview clone to origin/develop and run only the "
            "follow-up the change needs (reload / rebuild / migrate / npm build). "
            "Runs every 2 min on compute-03 as the scitex-hub-dev-preview-sync job.",
        ),
        examples=(
            (
                "{prog} dev-preview sync --dry-run --clone ~/proj/scitex-cloud",
                "Show what the next tick would do",
            ),
            ("{prog} dev-preview sync --clone ~/proj/scitex-cloud", "Run one tick now"),
        ),
    ),
)
def dev_preview() -> None:
    """Keep the develop preview current.

    \b
    Example:
        scitex-hub dev-preview sync --dry-run --clone ~/proj/scitex-cloud
        scitex-hub dev-preview sync --clone ~/proj/scitex-cloud
    """


@dev_preview.command("sync", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "--clone",
    type=click.Path(file_okay=False, path_type=Path),
    envvar="SCITEX_HUB_DEV_PREVIEW_CLONE",
    required=True,
    help="The bind-mounted clone the preview stack serves from.",
)
@click.option(
    "--remote", default="origin", show_default=True, help="Git remote to fetch."
)
@click.option(
    "--branch",
    default="develop",
    show_default=True,
    help="Branch the clone must be on.",
)
@click.option(
    "--container",
    default="scitex-hub-dev-django-1",
    show_default=True,
    help="Django container for docker exec / health polling.",
)
@click.option(
    "--state-dir",
    type=click.Path(file_okay=False, path_type=Path),
    envvar="SCITEX_HUB_DEV_PREVIEW_STATE_DIR",
    default=str(_DEFAULT_STATE_DIR),
    show_default=True,
    help="Where state.json, sync.log and the lock live.",
)
@click.option(
    "--dry-run", is_flag=True, help="Fetch and plan; move nothing, file no cards."
)
@click.option(
    "--no-cards",
    is_flag=True,
    envvar="SCITEX_HUB_DEV_PREVIEW_NO_CARDS",
    help=(
        "Run for real but only LOG what would be filed on the board. For "
        "manual runs against a scratch clone: a refusal or hold must not "
        "land on the operator's board as if the preview were stuck."
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit JSON (always on; accepted for uniformity).",
)
def sync_cmd(
    clone: Path,
    remote: str,
    branch: str,
    container: str,
    state_dir: Path,
    dry_run: bool,
    no_cards: bool,
    as_json: bool,
) -> None:
    """Run one sync tick: fetch, fast-forward, classify, act.

    Exit codes: 0 ok/noop/already-running/dry-run, 1 failed (retried next
    tick), 2 refused (clone needs a human), 3 held (too many failures at
    this commit).

    \b
    Example:
        scitex-hub dev-preview sync --dry-run --clone ~/proj/scitex-cloud
        scitex-hub dev-preview sync --clone ~/proj/scitex-cloud
    """
    del as_json  # output is JSON regardless; see module docstring
    resolved_state_dir = Path(state_dir).expanduser()

    # The board adapter is best effort and never raises; its failures are
    # only visible if they land in the same JSONL log as every other step.
    def log(record: dict) -> None:
        append_log(resolved_state_dir, record)

    cards = NullCardFiler(log=log) if no_cards else CliCardFiler(log=log)
    outcome = sync(
        Config(
            clone=Path(clone).expanduser(),
            state_dir=resolved_state_dir,
            remote=remote,
            branch=branch,
            container=container,
            dry_run=dry_run,
            cards=cards,
        )
    )
    click.echo(outcome.to_json())
    if outcome.exit_code:
        click.echo(f"dev-preview sync: {outcome.status} — {outcome.message}", err=True)
    sys.exit(outcome.exit_code)


# EOF
