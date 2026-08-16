#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync commands between Local, Gitea, and Workspace.

Architecture:
    Local (dev machine) ←→ Gitea (source of truth) ←→ Workspace (server-side)

Commands:
    push-project     — git push to Gitea (committed changes)
    pull-project     — git pull from Gitea (committed changes)
    workspace push   — sync working files to workspace (Dropbox-style)
    workspace pull   — sync working files from workspace (Dropbox-style)
    workspace status — show divergence across all three

The Dropbox-style family is mounted on the ``workspace`` noun group
(see workspace.py); doctrine §1d: directional transfer is push/pull
(never sync-to/sync-from) and short aliases like ``ss`` are banned.
The old root spellings survive as warn-phase deprecated aliases.
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from ._click_compat import (
    register_error_redirect,
    register_warn_alias,
    spec_command_kwargs,
)
from ._flags import (
    confirm_or_abort,
    dry_run_flag,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
    yes_flag,
)

console = Console()


def _get_ssh_target(env_name: str = "dev") -> tuple[str, int]:
    """Return (host, port) for SSH to the target environment."""
    from .ssh import SSH_HOSTS, SSH_PORTS

    return SSH_HOSTS.get(env_name, "127.0.0.1"), SSH_PORTS.get(env_name, 2200)


def _get_workspace_path(repo: str) -> str:
    """Resolve server-side workspace path for a repo (owner/name or name)."""
    if "/" in repo:
        owner, name = repo.split("/", 1)
    else:
        owner = _detect_owner()
        name = repo
    return f"/app/data/users/{owner}/proj/{name}"


def _detect_owner() -> str:
    """Detect repo owner from git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        for sep in [":", "/"]:
            parts = url.rstrip("/").rsplit(sep, 2)
            if len(parts) >= 2:
                candidate = parts[-2].split("/")[-1]
                if candidate and candidate not in ("git", "https", "http", ""):
                    return candidate
    except (subprocess.CalledProcessError, IndexError):
        pass
    return "ywatanabe"


def _detect_repo() -> str:
    """Detect repo name from current git directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip()).name
    except subprocess.CalledProcessError:
        return ""


def _is_on_workspace() -> bool:
    """Detect if we're running on the workspace server."""
    return Path("/app/data").is_dir()


def _resolve_repo(repo: str) -> str:
    """Resolve repo argument, auto-detecting if empty."""
    if repo:
        return repo
    name = _detect_repo()
    if not name:
        console.print("[red]Cannot detect repo. Provide REPO argument.[/red]")
        sys.exit(1)
    return f"{_detect_owner()}/{name}"


# ── push / pull (git ↔ Gitea) ────────────────────────────────────


@click.command("push")
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


@click.command("pull")
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


# ── workspace push / pull (Dropbox-style ↔ Workspace) ───────────


@click.command(
    "push",
    **spec_command_kwargs(
        summary="Sync working files to the workspace (Dropbox-style).",
        description=(
            "Detects conflicts when both sides changed since the last "
            "sync. Conflicted files are kept as "
            "file.conflict-<timestamp>.ext.",
        ),
        examples=(
            ("{prog} workspace push", "Auto-detect repo"),
            ("{prog} workspace push ywatanabe/my-proj", "Explicit repo"),
            ("{prog} workspace push --dry-run", "Preview changes"),
            ("{prog} workspace push ywatanabe/my-proj --yes", "Skip confirmation"),
        ),
    ),
)
@click.argument("repo", default="")
@click.option("--env", "env_name", default="dev", help="Target environment")
@dry_run_flag()
@yes_flag()
def sync_to(repo, env_name, dry_run, yes):
    """Sync working files to workspace (Dropbox-style).

    Detects conflicts when both sides changed since last sync.
    Conflicted files are kept as file.conflict-<timestamp>.ext.

    \b
    Example:
        scitex-hub workspace push                            # auto-detect repo
        scitex-hub workspace push ywatanabe/my-proj          # explicit repo
        scitex-hub workspace push --dry-run                  # preview changes
        scitex-hub workspace push ywatanabe/my-proj --yes
    """
    if _is_on_workspace():
        console.print(
            "[red]You're already on the workspace.[/red]\n"
            "[yellow]Did you mean: scitex cloud push[/yellow]"
        )
        sys.exit(1)

    repo = _resolve_repo(repo)
    host, port = _get_ssh_target(env_name)
    ws_path = _get_workspace_path(repo)

    if dry_run:
        # Engine has its own dry-run preview; fall through to call it so the
        # plan output matches real-run targeting. We also emit the uniform
        # [dry-run] prefix line so audit-cli sees the canonical marker.
        print_dry_run(
            f"sync local -> workspace ({repo}) via ssh -p {port} scitex@{host}:{ws_path}"
        )

    if not dry_run:
        confirm_or_abort(f"Sync local → workspace ({repo})?", yes=yes, dry_run=dry_run)

    ssh_cmd = ["ssh", "-p", str(port), f"scitex@{host}"]

    from ._sync_engine import sync_files

    console.print(f"[cyan]Syncing → workspace ({repo})[/cyan]")
    result = sync_files(Path.cwd(), ssh_cmd, ws_path, "to", dry_run=dry_run)
    _print_sync_result(result, dry_run)


@click.command(
    "pull",
    **spec_command_kwargs(
        summary="Sync working files from the workspace (Dropbox-style).",
        description=(
            "Detects conflicts when both sides changed since the last "
            "sync. Conflicted files are kept as "
            "file.conflict-<timestamp>.ext.",
        ),
        examples=(
            ("{prog} workspace pull", "Auto-detect repo"),
            ("{prog} workspace pull ywatanabe/my-proj", "Explicit repo"),
            ("{prog} workspace pull --dry-run", "Preview changes"),
            ("{prog} workspace pull ywatanabe/my-proj --yes", "Skip confirmation"),
        ),
    ),
)
@click.argument("repo", default="")
@click.option("--env", "env_name", default="dev", help="Target environment")
@dry_run_flag()
@yes_flag()
def sync_from(repo, env_name, dry_run, yes):
    """Sync working files from workspace (Dropbox-style).

    Detects conflicts when both sides changed since last sync.
    Conflicted files are kept as file.conflict-<timestamp>.ext.

    \b
    Example:
        scitex-hub workspace pull                          # auto-detect repo
        scitex-hub workspace pull ywatanabe/my-proj        # explicit repo
        scitex-hub workspace pull --dry-run                # preview changes
        scitex-hub workspace pull ywatanabe/my-proj --yes
    """
    if _is_on_workspace():
        console.print(
            "[red]You're already on the workspace.[/red]\n"
            "[yellow]Did you mean: scitex cloud pull[/yellow]"
        )
        sys.exit(1)

    repo = _resolve_repo(repo)
    host, port = _get_ssh_target(env_name)
    ws_path = _get_workspace_path(repo)

    if dry_run:
        print_dry_run(
            f"sync workspace -> local ({repo}) via ssh -p {port} scitex@{host}:{ws_path}"
        )

    if not dry_run:
        confirm_or_abort(f"Sync workspace → local ({repo})?", yes=yes, dry_run=dry_run)

    ssh_cmd = ["ssh", "-p", str(port), f"scitex@{host}"]

    from ._sync_engine import sync_files

    console.print(f"[cyan]Syncing ← workspace ({repo})[/cyan]")
    result = sync_files(Path.cwd(), ssh_cmd, ws_path, "from", dry_run=dry_run)
    _print_sync_result(result, dry_run)


def _print_sync_result(result, dry_run: bool) -> None:
    """Print sync results with conflict warnings."""
    prefix = "[dim](dry run)[/dim] " if dry_run else ""

    if result.synced:
        console.print(f"{prefix}[green]Synced {len(result.synced)} file(s)[/green]")
        for f in result.synced[:10]:
            console.print(f"  {f}")
        if len(result.synced) > 10:
            console.print(f"  ... and {len(result.synced) - 10} more")

    if result.conflicts:
        console.print(
            f"\n{prefix}[yellow]⚠ {len(result.conflicts)} conflict(s) "
            f"— both sides changed[/yellow]"
        )
        for f in result.conflicts:
            console.print(f"  [yellow]{f}[/yellow] → .conflict-* copy created")

    if result.errors:
        console.print(f"\n{prefix}[red]{len(result.errors)} error(s)[/red]")
        for e in result.errors:
            console.print(f"  [red]{e}[/red]")
        sys.exit(1)

    if not result.synced and not result.conflicts:
        console.print(f"{prefix}[green]Already in sync[/green]")


# ── workspace status ─────────────────────────────────────────────


@click.command(
    "status",
    **spec_command_kwargs(
        summary="Show sync state across Local, Gitea, and Workspace.",
        description=(
            "Read-only verb, but it fans out to `git fetch` plus an "
            "SSH probe, so the mutating flag pair applies: --dry-run "
            "short-circuits before any network call; --yes is a no-op "
            "for the read path but kept for symmetry.",
        ),
        examples=(
            ("{prog} workspace status", "Show 3-way sync state"),
            ("{prog} workspace status ywatanabe/my-proj --env prod", ""),
            ("{prog} workspace status --json", "Machine-readable output"),
            ("{prog} workspace status --dry-run", "Preview the probes"),
        ),
    ),
)
@click.argument("repo", default="")
@click.option("--env", "env_name", default="dev", help="Target environment")
@json_flag()
@mutating_flags()
def sync_status(repo, env_name, json_output, dry_run, yes):
    """Show sync state across Local, Gitea, and Workspace.

    Read-only verb, but the audit's §2 universal-flag check expects the
    mutating-pair on any noun-leaf that COULD invoke a remote action
    (it fans out to ``git fetch`` + an SSH probe). ``--dry-run``
    short-circuits before any network call; ``--yes`` is a no-op for the
    read path but kept for symmetry across the workspace family.

    \b
    Example:
        scitex-hub workspace status
        scitex-hub workspace status ywatanabe/my-proj --env prod
        scitex-hub workspace status --json
        scitex-hub workspace status --dry-run
    """
    if dry_run:
        print_dry_run(
            f"probe sync state (git fetch origin + remote `git rev-list`) "
            f"for repo='{repo or '<auto-detect>'}' env={env_name}"
        )
        return
    _ = yes  # symmetric flag; no confirmation required for a read verb
    from rich.table import Table

    rows: list[dict[str, str]] = []

    # Local ↔ Gitea
    try:
        subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        ahead, behind = result.stdout.strip().split()
        if ahead == "0" and behind == "0":
            lg = "in sync"
        else:
            lg = f"ahead={ahead} behind={behind}"
    except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
        lg = "unknown (git fetch failed)"
    rows.append({"pair": "local-gitea", "status": lg})

    # Workspace ↔ Gitea
    ws_row = None
    if repo or _detect_repo():
        repo = _resolve_repo(repo) if repo else f"{_detect_owner()}/{_detect_repo()}"
        host, port = _get_ssh_target(env_name)
        ws_path = _get_workspace_path(repo)
        ssh_prefix = ["ssh", "-p", str(port), f"scitex@{host}"]
        try:
            result = subprocess.run(
                ssh_prefix
                + [
                    f"cd {ws_path} && git fetch origin 2>/dev/null && "
                    f"git rev-list --left-right --count HEAD...origin/HEAD"
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            ahead, behind = result.stdout.strip().split()
            if ahead == "0" and behind == "0":
                wg = "in sync"
            else:
                wg = f"ahead={ahead} behind={behind}"
        except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
            wg = "unknown (SSH or repo not found)"
        ws_row = {"pair": "workspace-gitea", "status": wg, "repo": repo}
        rows.append(ws_row)

    if json_output:
        emit_json({"success": True, "rows": rows})
        return

    table = Table(title="Sync Status")
    table.add_column("Pair", style="cyan")
    table.add_column("Status")
    for row in rows:
        table.add_row(row["pair"], row["status"])
    console.print(table)


# ── Registration ─────────────────────────────────────────────────


def register_sync_commands(group: click.Group) -> None:
    """Register sync commands and deprecation aliases on the root group.

    The Dropbox-style leaves themselves (``sync_to``/``sync_from``/
    ``sync_status``) are mounted on the ``workspace`` noun group in
    workspace.py; here only their deprecated root spellings are kept as
    warn-phase aliases (removed in v0.20). ``ss`` was a banned short
    alias (doctrine §1d) and forwards to ``workspace status`` too.
    """
    push.name = "push-project"
    pull.name = "pull-project"
    group.add_command(push)
    group.add_command(pull)
    register_error_redirect(group, "push", target="push-project", remove_in="v0.20")
    register_error_redirect(group, "pull", target="pull-project", remove_in="v0.20")
    register_warn_alias(
        group,
        "sync-to",
        target=sync_to,
        remove_in="v0.20",
        target_name="workspace push",
    )
    register_warn_alias(
        group,
        "sync-from",
        target=sync_from,
        remove_in="v0.20",
        target_name="workspace pull",
    )
    register_warn_alias(
        group,
        "sync-status",
        target=sync_status,
        remove_in="v0.20",
        target_name="workspace status",
    )
    register_warn_alias(
        group,
        "ss",
        target=sync_status,
        remove_in="v0.20",
        target_name="workspace status",
    )


# EOF
