#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git-transport sync verbs: ``push-project`` / ``pull-project``.

Extracted from sync.py (512-line cap): these two leaves move COMMITTED
changes between Local and Gitea via plain ``git push`` / ``git pull``.
They are defined here with their registered short names (``push`` /
``pull``) and renamed to ``push-project`` / ``pull-project`` by
``sync.register_sync_commands`` — the single registration point.
"""

from __future__ import annotations

import subprocess
import sys

import click
from rich.console import Console

from ._click_compat import spec_command_kwargs
from ._flags import confirm_or_abort, mutating_flags, print_dry_run

console = Console()


@click.command(
    "push",
    **spec_command_kwargs(
        summary="Git push to Gitea (committed changes).",
        examples=(("{prog} push-project origin main --yes", "Push main to Gitea."),),
    ),
)
@click.argument("remote", default="origin")
@click.argument("branch", default="")
@mutating_flags()
def push(remote, branch, dry_run, yes):
    """Git push to Gitea (committed changes).

    \b
    Example:
        scitex-hub push-project                       # push to origin
        scitex-hub push-project origin main           # push main branch
        scitex-hub push-project --dry-run             # preview the git-push command
        scitex-hub push-project origin main --yes     # skip confirmation
    """
    cmd = ["git", "push", remote]
    if branch:
        cmd.append(branch)

    if dry_run:
        print_dry_run(f"exec: {' '.join(cmd)}")
        return

    confirm_or_abort(f"Run `{' '.join(cmd)}`?", yes=yes, dry_run=dry_run)

    try:
        subprocess.run(cmd, check=True)
        console.print("[green]Pushed → Gitea[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Push failed (exit {e.returncode})[/red]")
        sys.exit(e.returncode)


@click.command(
    "pull",
    **spec_command_kwargs(
        summary="Git pull from Gitea (committed changes).",
        examples=(("{prog} pull-project origin main --yes", "Pull main from Gitea."),),
    ),
)
@click.argument("remote", default="origin")
@click.argument("branch", default="")
@mutating_flags()
def pull(remote, branch, dry_run, yes):
    """Git pull from Gitea (committed changes).

    \b
    Example:
        scitex-hub pull-project                       # pull from origin
        scitex-hub pull-project origin main           # pull main branch
        scitex-hub pull-project --dry-run             # preview the git-pull command
        scitex-hub pull-project origin main --yes     # skip confirmation
    """
    cmd = ["git", "pull", remote]
    if branch:
        cmd.append(branch)

    if dry_run:
        print_dry_run(f"exec: {' '.join(cmd)}")
        return

    confirm_or_abort(f"Run `{' '.join(cmd)}`?", yes=yes, dry_run=dry_run)

    try:
        subprocess.run(cmd, check=True)
        console.print("[green]Pulled ← Gitea[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Pull failed (exit {e.returncode})[/red]")
        console.print("[yellow]Resolve merge conflicts, then retry.[/yellow]")
        sys.exit(e.returncode)


# EOF
