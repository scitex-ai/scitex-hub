#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync commands between Local, Gitea, and Workspace.

Architecture:
    Local (dev machine) ←→ Gitea (source of truth) ←→ Workspace (server-side)

Commands:
    push        — git push to Gitea (committed changes)
    pull        — git pull from Gitea (committed changes)
    sync-to     — sync working files to workspace (Dropbox-style, conflict-aware)
    sync-from   — sync working files from workspace (Dropbox-style, conflict-aware)
    sync-status — show divergence across all three
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

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
def push(remote, branch):
    """Git push to Gitea (committed changes).

    \b
    Examples:
        scitex cloud push              # push to origin
        scitex cloud push origin main  # push main branch
    """
    cmd = ["git", "push", remote]
    if branch:
        cmd.append(branch)
    try:
        subprocess.run(cmd, check=True)
        console.print("[green]Pushed → Gitea[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Push failed (exit {e.returncode})[/red]")
        sys.exit(e.returncode)


@click.command("pull")
@click.argument("remote", default="origin")
@click.argument("branch", default="")
def pull(remote, branch):
    """Git pull from Gitea (committed changes).

    \b
    Examples:
        scitex cloud pull              # pull from origin
        scitex cloud pull origin main  # pull main branch
    """
    cmd = ["git", "pull", remote]
    if branch:
        cmd.append(branch)
    try:
        subprocess.run(cmd, check=True)
        console.print("[green]Pulled ← Gitea[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Pull failed (exit {e.returncode})[/red]")
        console.print("[yellow]Resolve merge conflicts, then retry.[/yellow]")
        sys.exit(e.returncode)


# ── sync-to / sync-from (Dropbox-style ↔ Workspace) ─────────────


@click.command("sync-to")
@click.argument("repo", default="")
@click.option("--env", "env_name", default="dev", help="Target environment")
@click.option("--dry-run", is_flag=True, help="Preview without changing files")
def sync_to(repo, env_name, dry_run):
    """Sync working files to workspace (Dropbox-style).

    Detects conflicts when both sides changed since last sync.
    Conflicted files are kept as file.conflict-<timestamp>.ext.

    \b
    Examples:
        scitex cloud sync-to                    # auto-detect repo
        scitex cloud sync-to ywatanabe/my-proj  # explicit repo
        scitex cloud sync-to --dry-run          # preview changes
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
    ssh_cmd = ["ssh", "-p", str(port), f"scitex@{host}"]

    from ._sync_engine import sync_files

    console.print(f"[cyan]Syncing → workspace ({repo})[/cyan]")
    result = sync_files(Path.cwd(), ssh_cmd, ws_path, "to", dry_run=dry_run)
    _print_sync_result(result, dry_run)


@click.command("sync-from")
@click.argument("repo", default="")
@click.option("--env", "env_name", default="dev", help="Target environment")
@click.option("--dry-run", is_flag=True, help="Preview without changing files")
def sync_from(repo, env_name, dry_run):
    """Sync working files from workspace (Dropbox-style).

    Detects conflicts when both sides changed since last sync.
    Conflicted files are kept as file.conflict-<timestamp>.ext.

    \b
    Examples:
        scitex cloud sync-from                    # auto-detect repo
        scitex cloud sync-from ywatanabe/my-proj  # explicit repo
        scitex cloud sync-from --dry-run          # preview changes
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


# ── sync-status ──────────────────────────────────────────────────


@click.command("sync-status")
@click.argument("repo", default="")
@click.option("--env", "env_name", default="dev", help="Target environment")
def sync_status(repo, env_name):
    """Show sync state across Local, Gitea, and Workspace."""
    from rich.table import Table

    table = Table(title="Sync Status")
    table.add_column("Pair", style="cyan")
    table.add_column("Status")

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
            lg = "[green]in sync[/green]"
        else:
            lg = f"↑{ahead} ahead, ↓{behind} behind"
    except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
        lg = "[yellow]unknown (git fetch failed)[/yellow]"
    table.add_row("Local ↔ Gitea", lg)

    # Workspace ↔ Gitea
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
                wg = "[green]in sync[/green]"
            else:
                wg = f"↑{ahead} ahead, ↓{behind} behind"
        except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
            wg = "[yellow]unknown (SSH or repo not found)[/yellow]"
        table.add_row("Workspace ↔ Gitea", wg)

    console.print(table)


# ── Registration ─────────────────────────────────────────────────


def register_sync_commands(group: click.Group) -> None:
    """Register sync commands and aliases on a click Group."""
    group.add_command(push)
    group.add_command(pull)
    group.add_command(sync_to, "sync-to")
    group.add_command(sync_from, "sync-from")
    group.add_command(sync_status, "sync-status")
    group.add_command(sync_status, "ss")


# EOF
