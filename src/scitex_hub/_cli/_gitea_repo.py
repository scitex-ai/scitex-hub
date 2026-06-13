#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/_gitea_repo.py
"""Gitea CLI - Repository management commands (clone, create, list, search, delete, fork)."""

import subprocess
import sys
from pathlib import Path

import click

from ._flags import (
    confirm_or_abort,
    dry_run_flag,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
    yes_flag,
)
from ._gitea_utils import get_gitea_http_url, get_tea_config, run_tea


@click.command()
@click.argument("repository")
@click.argument("destination", required=False)
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@mutating_flags()
def clone(repository, destination, login, dry_run, yes):
    """Clone a repository from SciTeX Hub.

    \b
    Example:
      $ scitex-hub gitea clone scitex-hub
      $ scitex-hub gitea clone scitex-dev/scitex-hub ./hub --yes
    """
    if dry_run:
        target = destination or "<basename of repo>"
        print_dry_run(
            f"clone repository '{repository}' into '{target}' via tea login '{login}'"
        )
        return
    confirm_or_abort(f"Clone repository '{repository}'?", yes=yes, dry_run=dry_run)
    if "/" not in repository:
        try:
            result = subprocess.run(
                [
                    str(Path.home() / ".local" / "bin" / "tea"),
                    "repos",
                    "ls",
                    "--login",
                    login,
                    "--fields",
                    "name,owner",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.split("\n"):
                if repository in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        owner = parts[1].strip()
                        if owner and owner != "OWNER":
                            repository = f"{owner}/{repository}"
                            break
            if "/" not in repository:
                click.echo(f"Error: Repository '{repository}' not found.", err=True)
                sys.exit(1)
        except subprocess.CalledProcessError:
            click.echo("Error: Could not list repositories.", err=True)
            sys.exit(1)
    args = ["clone", "--login", login, repository]
    if destination:
        args.append(destination)
    run_tea(*args)


@click.command()
@click.argument("name")
@click.option("--description", "-d", help="Repository description")
@click.option("--private", is_flag=True, help="Make repository private")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.option("--push", "do_push", is_flag=True, help="Do initial push after creating")
@click.option("--remote", default="scitex", help="Remote name to add (default: scitex)")
@mutating_flags()
def create(name, description, private, login, do_push, remote, dry_run, yes):
    """Create a new repository on Gitea.

    Also adds a Gitea remote to the current git repo (if in one) and
    prints the clone URL.  Use --push to immediately push the current branch.

    \b
    Example:
      $ scitex-hub gitea create my-new-repo --description "demo" --yes
      $ scitex-hub gitea create my-new-repo --private --push
    """
    if dry_run:
        visibility = "private" if private else "public"
        print_dry_run(
            f"create {visibility} Gitea repository '{name}' via tea login '{login}'"
            + (f" then push current branch to remote '{remote}'" if do_push else "")
        )
        return
    confirm_or_abort(f"Create repository '{name}'?", yes=yes, dry_run=dry_run)
    args = ["repo", "create", "--name", name, "--login", login]
    if description:
        args.extend(["--description", description])
    if private:
        args.append("--private")
    run_tea(*args)

    if Path(".git").exists() or _in_git_repo():
        try:
            cfg = get_tea_config(login)
            owner = cfg.get("user", "")
            if owner:
                clone_url = f"{cfg['url'].rstrip('/')}/{owner}/{name}.git"
                click.echo(f"Clone URL: {clone_url}")
                auth_url = get_gitea_http_url(owner, name, login)
                result = subprocess.run(
                    ["git", "remote", "get-url", remote],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    subprocess.run(
                        ["git", "remote", "add", remote, auth_url], check=True
                    )
                    click.echo(f"Remote '{remote}' added.")
                else:
                    click.echo(f"Remote '{remote}' already exists, skipping.")
                if do_push:
                    branch_result = subprocess.run(
                        ["git", "branch", "--show-current"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    branch = branch_result.stdout.strip() or "main"
                    click.echo(f"Pushing {branch} to {remote}...")
                    subprocess.run(["git", "push", "-u", remote, branch], check=True)
                    click.echo(f"Pushed {branch} -> {remote}/{branch}")
        except subprocess.CalledProcessError as e:
            click.echo(f"Warning: post-create git step failed: {e}", err=True)


def _in_git_repo():
    """Return True if cwd is inside a git repo."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@click.command(name="list")
@click.option("--user", "-u", help="List repos for specific user")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.option("--starred", "-s", is_flag=True, help="List starred repos")
@click.option("--watched", "-w", is_flag=True, help="List watched repos")
@json_flag()
def list_repos(user, login, starred, watched, json_output):
    """List repositories.

    \b
    Example:
      $ scitex-hub gitea list
      $ scitex-hub gitea list --user scitex-dev --json
    """
    args = ["repos", "--login", login]
    if json_output:
        args.extend(["--output", "json"])
    else:
        args.extend(["--output", "table"])
    if starred:
        args.append("--starred")
    if watched:
        args.append("--watched")
    if user:
        args.append(user)
    if json_output:
        # Capture tea output and re-emit as canonical JSON so callers don't
        # have to trust tea's raw text formatting.
        try:
            tea_bin = str(Path.home() / ".local" / "bin" / "tea")
            result = subprocess.run(
                [tea_bin, *args], capture_output=True, text=True, check=True
            )
            import json as _json

            try:
                payload = _json.loads(result.stdout or "[]")
            except _json.JSONDecodeError:
                payload = {"raw": result.stdout}
            emit_json(payload)
        except subprocess.CalledProcessError as e:
            emit_json({"error": str(e), "stderr": e.stderr})
            sys.exit(1)
        return
    run_tea(*args)


@click.command()
@click.argument("query")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.option("--limit", type=int, default=10, help="Maximum results")
@json_flag()
def search(query, login, limit, json_output):
    """Search for repositories.

    \b
    Example:
      $ scitex-hub gitea search scholar
      $ scitex-hub gitea search scholar --limit 5 --json
    """
    args = ["repos", "search", "--login", login, "--limit", str(limit), query]
    if json_output:
        try:
            tea_bin = str(Path.home() / ".local" / "bin" / "tea")
            result = subprocess.run(
                [tea_bin, *args, "--output", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            import json as _json

            try:
                payload = _json.loads(result.stdout or "[]")
            except _json.JSONDecodeError:
                payload = {"raw": result.stdout}
            emit_json(payload)
        except subprocess.CalledProcessError as e:
            emit_json({"error": str(e), "stderr": e.stderr})
            sys.exit(1)
        return
    run_tea(*args)


@click.command()
@click.argument("repository")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Confirm destructive action (required for non-interactive use)",
)
@dry_run_flag()
def delete(repository, login, yes, dry_run):
    """Delete a repository (DANGEROUS!). Requires --yes/-y (no prompt).

    \b
    Example:
      $ scitex-hub gitea delete scitex-dev/old-repo --yes
      $ scitex-hub gitea delete scitex-dev/old-repo --dry-run
    """
    if dry_run:
        print_dry_run(
            f"delete repository '{repository}' via Gitea API (login '{login}')"
        )
        return
    if not yes:
        click.echo(
            f"error: pass --yes/-y to confirm destructive action: "
            f"delete repository '{repository}'",
            err=True,
        )
        sys.exit(2)
    import requests
    import yaml

    config_path = Path.home() / ".config" / "tea" / "config.yml"
    if not config_path.exists():
        click.echo("Error: Tea configuration not found", err=True)
        sys.exit(1)
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        login_config = None
        for entry in config.get("logins", []):
            if entry["name"] == login:
                login_config = entry
                break
        if not login_config:
            click.echo(f"Error: Login '{login}' not found", err=True)
            sys.exit(1)
        if "/" not in repository:
            click.echo("Error: Repository must be in format 'username/repo'", err=True)
            sys.exit(1)
        owner, repo = repository.split("/", 1)
        api_url = f"{login_config['url']}/api/v1/repos/{owner}/{repo}"
        headers = {"Authorization": f"token {login_config['token']}"}
        response = requests.delete(api_url, headers=headers)
        if response.status_code == 204:
            click.echo(f"Repository '{repository}' deleted successfully")
        elif response.status_code == 404:
            click.echo(f"Error: Repository '{repository}' not found", err=True)
            sys.exit(1)
        else:
            click.echo(
                f"Error: Failed to delete (status {response.status_code})", err=True
            )
            sys.exit(1)
    except ImportError:
        click.echo("Error: PyYAML not installed", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("repository")
def fork(repository):
    """Fork a repository.

    \b
    Example:
      $ scitex-hub gitea fork scitex-dev/scitex-hub
    """
    run_tea("repo", "fork", repository)


# EOF
