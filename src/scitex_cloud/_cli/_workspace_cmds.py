#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/_workspace_cmds.py
"""Workspace CLI - upload, list, sync, logout commands."""

import json
import os
import subprocess
import sys
from pathlib import Path

import click
import requests

from ._workspace_auth import (
    TOKEN_CACHE_PATH,
    auth_headers,
    get_jwt_token,
    get_server_url,
)

_DEFAULT_SERVER = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _in_git_repo():
    """Return True when cwd is inside a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _current_branch():
    """Return the current git branch name, or None."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _setup_remote_and_push(server_url, username, project_name, remote_name):
    """Add the Gitea remote (with token auth if available) and push."""
    from ._gitea_utils import get_gitea_url, get_tea_config

    try:
        cfg = get_tea_config("scitex-dev")
        owner = cfg.get("user", username)
        gitea_base = cfg["url"].rstrip("/")
        token = cfg["token"]
        if "://" in gitea_base:
            scheme, rest = gitea_base.split("://", 1)
        else:
            scheme, rest = "http", gitea_base
        remote_url = f"{scheme}://{token}@{rest}/{owner}/{project_name}.git"
    except SystemExit:
        gitea_base = get_gitea_url()
        remote_url = f"{gitea_base}/{username}/{project_name}.git"
        click.echo(
            "Warning: tea CLI not configured. Using unauthenticated remote URL.",
            err=True,
        )
        click.echo(
            "Run 'scitex-cloud gitea login' to configure authenticated access.",
            err=True,
        )

    check = subprocess.run(
        ["git", "remote", "get-url", remote_name],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        try:
            subprocess.run(
                ["git", "remote", "add", remote_name, remote_url],
                check=True,
            )
            click.echo(f"Remote '{remote_name}' added.")
        except subprocess.CalledProcessError as exc:
            click.echo(f"Error adding git remote: {exc}", err=True)
            sys.exit(1)
    else:
        click.echo(f"Remote '{remote_name}' already exists.")

    branch = _current_branch() or "main"
    click.echo(f"Pushing {branch} -> {remote_name}/{branch} ...")
    try:
        subprocess.run(["git", "push", "-u", remote_name, branch], check=True)
        click.echo("Pushed successfully.")
    except subprocess.CalledProcessError as exc:
        click.echo(f"Error: git push failed: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@click.command("upload")
@click.option(
    "--name", "-n", default=None, help="Project name (default: directory name)"
)
@click.option("--description", "-d", default="", help="Project description")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_CLOUD_URL",
    default=_DEFAULT_SERVER,
    show_default=True,
    help="SciTeX Cloud server URL",
)
@click.option(
    "--visibility",
    type=click.Choice(["private", "public"]),
    default="private",
    show_default=True,
    help="Repository visibility",
)
@click.option(
    "--remote",
    default="scitex",
    show_default=True,
    help="Git remote name to add",
)
@click.option(
    "--push/--no-push",
    default=True,
    help="Push code after creating the project (default: yes)",
)
def upload(name, description, server, visibility, remote, push):
    """Upload current directory as a new workspace project.

    Creates a project record on the SciTeX server, which auto-creates a
    Gitea repository.  The local git repo is then configured with the
    new remote and pushed.

    \b
    Similar to: gh repo create --push
    """
    server = get_server_url(server)
    project_name = name or Path(os.getcwd()).name

    token = get_jwt_token(server)

    click.echo(f"Creating project '{project_name}' on {server} ...")
    payload = {
        "name": project_name,
        "description": description,
        "visibility": visibility,
    }
    try:
        resp = requests.post(
            f"{server}/api/project/create/",
            json=payload,
            headers=auth_headers(token),
            timeout=30,
        )
    except requests.ConnectionError as exc:
        click.echo(f"Error: Connection failed: {exc}", err=True)
        sys.exit(1)

    if resp.status_code not in (200, 201):
        click.echo(
            f"Error: Project creation failed (HTTP {resp.status_code}).", err=True
        )
        click.echo(resp.text, err=True)
        sys.exit(1)

    data = resp.json()
    if not data.get("success"):
        click.echo(
            f"Error: {data.get('error', 'Unknown error from server')}",
            err=True,
        )
        sys.exit(1)

    project_id = data.get("project_id")
    slug = data.get("slug", project_name)
    project_url = data.get("url", "")
    click.echo(f"Project created: {slug} (id={project_id})")
    if project_url:
        click.echo(f"URL: {server}{project_url}")

    if not push:
        click.echo("Skipping git push (--no-push).")
        return

    if not _in_git_repo():
        click.echo("Warning: Not in a git repository — skipping git push.", err=True)
        return

    # Extract username from the project URL (/<username>/<slug>/)
    username = project_url.strip("/").split("/")[0] if project_url else project_name
    _setup_remote_and_push(server, username, slug, remote)


@click.command("list")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_CLOUD_URL",
    default=_DEFAULT_SERVER,
    show_default=True,
    help="SciTeX Cloud server URL",
)
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def list_projects(server, as_json):
    """List your projects on the SciTeX workspace.

    \b
    Similar to: gh repo list
    """
    server = get_server_url(server)
    token = get_jwt_token(server)

    try:
        resp = requests.get(
            f"{server}/api/project/list/",
            headers=auth_headers(token),
            timeout=15,
        )
    except requests.ConnectionError as exc:
        click.echo(f"Error: Connection failed: {exc}", err=True)
        sys.exit(1)

    if resp.status_code != 200:
        click.echo(
            f"Error: Failed to fetch project list (HTTP {resp.status_code}).",
            err=True,
        )
        sys.exit(1)

    projects = resp.json().get("projects", [])

    if as_json:
        click.echo(json.dumps(projects, indent=2, default=str))
        return

    if not projects:
        click.echo("No projects found.")
        return

    col_id = max(len("ID"), max(len(str(p["id"])) for p in projects))
    col_name = max(len("NAME"), max(len(p["name"]) for p in projects))
    col_desc = min(
        50,
        max(len("DESCRIPTION"), max(len(p.get("description") or "") for p in projects)),
    )

    header = (
        f"{'ID':<{col_id}}  {'NAME':<{col_name}}  {'DESCRIPTION':<{col_desc}}  UPDATED"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for p in projects:
        desc = (p.get("description") or "")[:50]
        updated = str(p.get("updated_at", ""))[:19]
        click.echo(
            f"{p['id']:<{col_id}}  {p['name']:<{col_name}}  {desc:<{col_desc}}  {updated}"
        )


@click.command("sync")
@click.option(
    "--remote",
    default="scitex",
    show_default=True,
    help="Git remote name to sync with",
)
@click.option(
    "--direction",
    type=click.Choice(["push", "pull", "both"]),
    default="both",
    show_default=True,
    help="Sync direction",
)
def sync(remote, direction):
    """Sync local repo with workspace (pull and/or push).

    \b
    Similar to: git pull origin <branch> && git push origin <branch>
    """
    if not _in_git_repo():
        click.echo("Error: Not in a git repository.", err=True)
        sys.exit(1)

    branch = _current_branch()
    if not branch:
        click.echo("Error: Not on any branch.", err=True)
        sys.exit(1)

    check = subprocess.run(
        ["git", "remote", "get-url", remote], capture_output=True, text=True
    )
    if check.returncode != 0:
        click.echo(f"Error: Remote '{remote}' not found.", err=True)
        click.echo(
            "Run 'scitex-cloud workspace upload' to create the project first.",
            err=True,
        )
        sys.exit(1)

    if direction in ("pull", "both"):
        click.echo(f"Pulling {remote}/{branch} ...")
        try:
            subprocess.run(["git", "pull", remote, branch], check=True)
        except subprocess.CalledProcessError as exc:
            click.echo(f"Error: git pull failed: {exc}", err=True)
            sys.exit(1)

    if direction in ("push", "both"):
        click.echo(f"Pushing {branch} -> {remote}/{branch} ...")
        try:
            subprocess.run(["git", "push", remote, branch], check=True)
        except subprocess.CalledProcessError as exc:
            click.echo(f"Error: git push failed: {exc}", err=True)
            sys.exit(1)

    click.echo("Sync complete.")


@click.command("logout")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_CLOUD_URL",
    default=_DEFAULT_SERVER,
    show_default=True,
    help="SciTeX Cloud server URL",
)
def logout(server):
    """Clear the cached JWT token for the given server."""
    server = get_server_url(server)
    if not TOKEN_CACHE_PATH.exists():
        click.echo("No cached token found.")
        return
    try:
        cached = json.loads(TOKEN_CACHE_PATH.read_text())
        if cached.get("server") == server:
            TOKEN_CACHE_PATH.unlink()
            click.echo(f"Cleared cached token for {server}.")
        else:
            click.echo(
                f"Cached token is for '{cached.get('server')}', not '{server}'.",
                err=True,
            )
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error clearing token: {exc}", err=True)
        sys.exit(1)


# EOF
