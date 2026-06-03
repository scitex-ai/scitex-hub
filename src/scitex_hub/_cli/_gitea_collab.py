#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/_gitea_collab.py
"""Gitea CLI - Collaboration commands (pr, issue, push, pull, status, enrich)."""

import subprocess
import sys
import time

import click
import requests

from ._gitea_utils import ensure_gitea_remote, ensure_not_in_workspace, run_tea

# ---------------------------------------------------------------------------
# Pull request group
# ---------------------------------------------------------------------------


@click.group()
def pr():
    """Pull request operations"""
    pass


@pr.command(name="create")
@click.option("--title", "-t", help="PR title")
@click.option("--description", "-d", help="PR description")
@click.option("--base", "-b", default="main", help="Base branch")
@click.option("--head", "-h", help="Head branch")
def pr_create(title, description, base, head):
    """Create a pull request"""
    args = ["pr", "create"]
    if title:
        args.extend(["--title", title])
    if description:
        args.extend(["--description", description])
    if base:
        args.extend(["--base", base])
    if head:
        args.extend(["--head", head])
    run_tea(*args)


@pr.command(name="list")
def pr_list():
    """List pull requests"""
    run_tea("pr", "list")


# ---------------------------------------------------------------------------
# Issue group
# ---------------------------------------------------------------------------


@click.group()
def issue():
    """Issue operations"""
    pass


@issue.command(name="create")
@click.option("--title", "-t", required=True, help="Issue title")
@click.option("--body", "-b", help="Issue body")
def issue_create(title, body):
    """Create an issue"""
    args = ["issue", "create", "--title", title]
    if body:
        args.extend(["--body", body])
    run_tea(*args)


@issue.command(name="list")
def issue_list():
    """List issues"""
    run_tea("issue", "list")


# ---------------------------------------------------------------------------
# Git workflow commands
# ---------------------------------------------------------------------------


@click.command()
@click.option("--remote", default="scitex", help="Remote name (default: scitex)")
@click.option(
    "--branch", "branch_opt", default=None, help="Branch to push (default: current)"
)
@click.option("--repo", default=None, help="Override repo name (default: cwd name)")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
def push(remote, branch_opt, repo, login):
    """Push local changes to Gitea.

    Sets up the Gitea remote with token authentication if it does not exist,
    then pushes the specified (or current) branch.
    """
    ensure_not_in_workspace()
    try:
        if branch_opt:
            branch = branch_opt
        else:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()
            if not branch:
                click.echo("Error: Not on any branch", err=True)
                sys.exit(1)

        ensure_gitea_remote(remote_name=remote, login_name=login, repo=repo)

        click.echo(f"Pushing {branch} -> {remote}/{branch} ...")
        subprocess.run(["git", "push", "-u", remote, branch], check=True)
        click.echo(f"Pushed {branch} -> {remote}/{branch}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
def pull():
    """Pull workspace changes to local machine"""
    ensure_not_in_workspace()
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        if not branch:
            click.echo("Error: Not on any branch", err=True)
            sys.exit(1)
        click.echo("Pulling from workspace...")
        subprocess.run(["git", "pull", "origin", branch], check=True)
        click.echo(f"Pulled from workspace (origin/{branch})")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command("show-status")
def status():
    """Show repository status"""
    ensure_not_in_workspace()
    subprocess.run(["git", "status"])


# ---------------------------------------------------------------------------
# Scholar enrichment
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True),
    help="Input BibTeX file",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    required=True,
    type=click.Path(),
    help="Output BibTeX file",
)
@click.option(
    "-a",
    "--api-key",
    envvar="SCITEX_HUB_API_KEY",
    help="SciTeX API key (or set SCITEX_HUB_API_KEY)",
)
@click.option("--no-cache", is_flag=True, help="Disable cache")
@click.option("--url", default="https://scitex.ai", help="SciTeX Hub URL")
def enrich(input_file, output_file, api_key, no_cache, url):
    """Enrich BibTeX file with metadata"""
    if not api_key:
        click.echo("Error: API key required", err=True)
        click.echo("Set SCITEX_HUB_API_KEY or use --api-key", err=True)
        sys.exit(1)
    click.echo(f"Enriching: {input_file}")
    with open(input_file, "rb") as f:
        files = {"bibtex_file": f}
        data = {"use_cache": "false" if no_cache else "true"}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Requested-With": "XMLHttpRequest",
        }
        response = requests.post(
            f"{url}/scholar/bibtex/upload/", headers=headers, files=files, data=data
        )
    if response.status_code != 200:
        click.echo(f"Error: Upload failed ({response.status_code})", err=True)
        sys.exit(1)
    result = response.json()
    if not result.get("success"):
        click.echo(f"Error: {result.get('error', 'Upload failed')}", err=True)
        sys.exit(1)
    job_id = result["job_id"]
    click.echo(f"Job ID: {job_id}")
    click.echo("Processing", nl=False)
    while True:
        response = requests.get(
            f"{url}/scholar/api/bibtex/job/{job_id}/status/", headers=headers
        )
        data = response.json()
        job_status = data["status"]
        if job_status == "completed":
            click.echo(" Done!")
            break
        elif job_status in ("failed", "cancelled"):
            click.echo(f" {job_status.capitalize()}!", err=True)
            sys.exit(1)
        click.echo(".", nl=False)
        time.sleep(2)
    response = requests.get(
        f"{url}/scholar/api/bibtex/job/{job_id}/download/", headers=headers
    )
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        click.echo(f"Saved: {output_file}")
    else:
        click.echo("Error: Download failed", err=True)
        sys.exit(1)


# EOF
