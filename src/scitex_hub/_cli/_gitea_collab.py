#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/_gitea_collab.py
"""Gitea CLI - Collaboration commands (pr, issue, push, pull, status, enrich)."""

import subprocess
import sys
import time

import click
import requests

from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._flags import (
    confirm_or_abort,
    dry_run_flag,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
)
from ._gitea_utils import ensure_gitea_remote, ensure_not_in_workspace, run_tea

# ---------------------------------------------------------------------------
# Pull request group
# ---------------------------------------------------------------------------


@click.group(
    **spec_group_kwargs(
        summary="Pull request operations.",
        examples=(
            ("{prog} gitea pr create --title Fix --base develop --yes", ""),
            ("{prog} gitea pr list --json", "List PRs as JSON"),
        ),
        command_categories=[("Core", ["create", "list"])],
    )
)
def pr():
    """Pull request operations"""
    pass


@pr.command(
    name="create",
    **spec_command_kwargs(
        summary="Create a pull request.",
        examples=(
            ("{prog} gitea pr create --title 'Fix audit' --base develop --yes", ""),
            ("{prog} gitea pr create -t WIP --dry-run", "Preview only"),
        ),
    ),
)
@click.option("--title", "-t", help="PR title")
@click.option("--description", "-d", help="PR description")
@click.option("--base", "-b", default="main", help="Base branch")
@click.option("--head", "-h", help="Head branch")
@mutating_flags()
def pr_create(title, description, base, head, dry_run, yes):
    """Create a pull request.

    \b
    Example:
      $ scitex-hub gitea pr create --title "Fix audit" --base develop --yes
      $ scitex-hub gitea pr create -t "WIP" --dry-run
    """
    if dry_run:
        print_dry_run(
            f"open pull request '{title or '<no title>'}' "
            f"({head or 'current'} -> {base})"
        )
        return
    confirm_or_abort(
        f"Open pull request '{title or '<no title>'}'?", yes=yes, dry_run=dry_run
    )
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


@pr.command(
    name="list",
    **spec_command_kwargs(
        summary="List pull requests.",
        examples=(
            ("{prog} gitea pr list", "List open PRs"),
            ("{prog} gitea pr list --json", "Machine-readable output"),
        ),
    ),
)
@json_flag()
def pr_list(json_output):
    """List pull requests.

    \b
    Example:
      $ scitex-hub gitea pr list
      $ scitex-hub gitea pr list --json
    """
    if json_output:
        try:
            from pathlib import Path

            tea_bin = str(Path.home() / ".local" / "bin" / "tea")
            result = subprocess.run(
                [tea_bin, "pr", "list", "--output", "json"],
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
    run_tea("pr", "list")


# ---------------------------------------------------------------------------
# Issue group
# ---------------------------------------------------------------------------


@click.group(
    **spec_group_kwargs(
        summary="Issue operations.",
        examples=(
            ("{prog} gitea issue create --title 'Bug X' --yes", "Open an issue"),
            ("{prog} gitea issue list --json", "List issues as JSON"),
        ),
        command_categories=[("Core", ["create", "list"])],
    )
)
def issue():
    """Issue operations"""
    pass


@issue.command(
    name="create",
    **spec_command_kwargs(
        summary="Create an issue.",
        examples=(
            ("{prog} gitea issue create --title 'Bug X' --yes", ""),
            ("{prog} gitea issue create -t 'Audit follow-up' --dry-run", "Preview"),
        ),
    ),
)
@click.option("--title", "-t", required=True, help="Issue title")
@click.option("--body", "-b", help="Issue body")
@mutating_flags()
def issue_create(title, body, dry_run, yes):
    """Create an issue.

    \b
    Example:
      $ scitex-hub gitea issue create --title "Bug X" --yes
      $ scitex-hub gitea issue create -t "Audit follow-up" --dry-run
    """
    if dry_run:
        print_dry_run(f"open issue '{title}'")
        return
    confirm_or_abort(f"Open issue '{title}'?", yes=yes, dry_run=dry_run)
    args = ["issue", "create", "--title", title]
    if body:
        args.extend(["--body", body])
    run_tea(*args)


@issue.command(
    name="list",
    **spec_command_kwargs(
        summary="List issues.",
        examples=(
            ("{prog} gitea issue list", "List open issues"),
            ("{prog} gitea issue list --json", "Machine-readable output"),
        ),
    ),
)
@json_flag()
def issue_list(json_output):
    """List issues.

    \b
    Example:
      $ scitex-hub gitea issue list
      $ scitex-hub gitea issue list --json
    """
    if json_output:
        try:
            from pathlib import Path

            tea_bin = str(Path.home() / ".local" / "bin" / "tea")
            result = subprocess.run(
                [tea_bin, "issue", "list", "--output", "json"],
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
    run_tea("issue", "list")


# ---------------------------------------------------------------------------
# Git workflow commands
# ---------------------------------------------------------------------------


@click.command(
    "push",
    **spec_command_kwargs(
        summary="Push local changes to Gitea.",
        description=(
            "Sets up the Gitea remote with token authentication if it "
            "does not exist, then pushes the specified (or current) "
            "branch.",
        ),
        examples=(
            ("{prog} gitea push --yes", "Push current branch"),
            ("{prog} gitea push --branch develop --dry-run", "Preview a push"),
        ),
    ),
)
@click.option("--remote", default="scitex", help="Remote name (default: scitex)")
@click.option(
    "--branch", "branch_opt", default=None, help="Branch to push (default: current)"
)
@click.option("--repo", default=None, help="Override repo name (default: cwd name)")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@mutating_flags()
def push(remote, branch_opt, repo, login, dry_run, yes):
    """Push local changes to Gitea.

    Sets up the Gitea remote with token authentication if it does not exist,
    then pushes the specified (or current) branch.

    \b
    Example:
      $ scitex-hub gitea push --yes
      $ scitex-hub gitea push --branch develop --dry-run
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

        if dry_run:
            print_dry_run(
                f"git push -u {remote} {branch} (after ensuring remote '{remote}' "
                f"is configured with login '{login}')"
            )
            return
        confirm_or_abort(f"Push {branch} to {remote}?", yes=yes, dry_run=dry_run)

        ensure_gitea_remote(remote_name=remote, login_name=login, repo=repo)

        click.echo(f"Pushing {branch} -> {remote}/{branch} ...")
        subprocess.run(["git", "push", "-u", remote, branch], check=True)
        click.echo(f"Pushed {branch} -> {remote}/{branch}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command(
    "pull",
    **spec_command_kwargs(
        summary="Pull workspace changes to local machine.",
        examples=(
            ("{prog} gitea pull --yes", "Pull the current branch"),
            ("{prog} gitea pull --dry-run", "Preview the git-pull command"),
        ),
    ),
)
@mutating_flags()
def pull(dry_run, yes):
    """Pull workspace changes to local machine.

    \b
    Example:
      $ scitex-hub gitea pull --yes
      $ scitex-hub gitea pull --dry-run
    """
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
        if dry_run:
            print_dry_run(f"git pull origin {branch}")
            return
        confirm_or_abort(
            f"Pull origin/{branch} into current branch?", yes=yes, dry_run=dry_run
        )
        click.echo("Pulling from workspace...")
        subprocess.run(["git", "pull", "origin", branch], check=True)
        click.echo(f"Pulled from workspace (origin/{branch})")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command(
    "status",
    **spec_command_kwargs(
        summary="Show repository status.",
        examples=(
            ("{prog} gitea status", "Human-readable git status"),
            ("{prog} gitea status --json", "Machine-readable output"),
        ),
    ),
)
@json_flag()
def status(json_output):
    """Show repository status.

    \b
    Example:
      $ scitex-hub gitea status
      $ scitex-hub gitea status --json
    """
    ensure_not_in_workspace()
    if json_output:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain=v2", "--branch"],
                capture_output=True,
                text=True,
                check=True,
            )
            entries = []
            branch_info = {}
            for line in result.stdout.splitlines():
                if line.startswith("# branch."):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        branch_info[parts[1].replace("branch.", "")] = parts[2]
                elif line:
                    entries.append(line)
            emit_json({"branch": branch_info, "entries": entries})
        except subprocess.CalledProcessError as e:
            emit_json({"error": str(e), "stderr": e.stderr})
            sys.exit(1)
        return
    subprocess.run(["git", "status"])


# ---------------------------------------------------------------------------
# Scholar enrichment
# ---------------------------------------------------------------------------


@click.command(
    "enrich",
    **spec_command_kwargs(
        summary="Enrich BibTeX file with metadata.",
        examples=(
            ("{prog} gitea enrich -i refs.bib -o refs.enriched.bib", ""),
        ),
    ),
)
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
@click.option("--url", default="https://scitex.cloud", help="SciTeX Hub URL")
def enrich(input_file, output_file, api_key, no_cache, url):
    """Enrich BibTeX file with metadata.

    \b
    Example:
      $ scitex-hub gitea enrich -i refs.bib -o refs.enriched.bib
    """
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
