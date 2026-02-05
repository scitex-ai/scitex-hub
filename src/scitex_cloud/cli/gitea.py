#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/gitea.py
"""
SciTeX Cloud Gitea Commands - Wrapper for tea (Gitea CLI)

Provides git/repository operations by wrapping the tea command.
Usage: scitex-cloud gitea {login,clone,create,list,search,delete,fork,pr,issue,push,pull,status,enrich}
"""

import subprocess
import sys
from pathlib import Path

import click

from ._gitea_utils import ensure_not_in_workspace, run_tea


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def gitea():
    """
    Gitea operations (wraps tea CLI)

    \b
    Provides standard git hosting operations:
    - Repository management (create, list, delete)
    - Cloning and forking
    - Pull requests and issues

    \b
    Backend: Gitea (git.scitex.ai)
    """
    pass


@gitea.command()
@click.option("--url", default="http://localhost:3001", help="Gitea instance URL")
@click.option("--token", help="API token")
def login(url, token):
    """Login to SciTeX Cloud (Gitea)"""
    args = ["login", "add", "--name", "scitex", "--url", url]
    if token:
        args.extend(["--token", token])
    run_tea(*args)


@gitea.command()
@click.argument("repository")
@click.argument("destination", required=False)
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
def clone(repository, destination, login):
    """Clone a repository from SciTeX Cloud"""
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


@gitea.command()
@click.argument("name")
@click.option("--description", "-d", help="Repository description")
@click.option("--private", is_flag=True, help="Make repository private")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
def create(name, description, private, login):
    """Create a new repository"""
    args = ["repo", "create", "--name", name, "--login", login]
    if description:
        args.extend(["--description", description])
    if private:
        args.append("--private")
    run_tea(*args)


@gitea.command(name="list")
@click.option("--user", "-u", help="List repos for specific user")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.option("--starred", "-s", is_flag=True, help="List starred repos")
@click.option("--watched", "-w", is_flag=True, help="List watched repos")
def list_repos(user, login, starred, watched):
    """List repositories"""
    args = ["repos", "--login", login, "--output", "table"]
    if starred:
        args.append("--starred")
    if watched:
        args.append("--watched")
    if user:
        args.append(user)
    run_tea(*args)


@gitea.command()
@click.argument("query")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.option("--limit", type=int, default=10, help="Maximum results")
def search(query, login, limit):
    """Search for repositories"""
    run_tea("repos", "search", "--login", login, "--limit", str(limit), query)


@gitea.command()
@click.argument("repository")
@click.option("--login", "-l", default="scitex-dev", help="Tea login to use")
@click.confirmation_option(prompt="Are you sure you want to delete this repository?")
def delete(repository, login):
    """Delete a repository (DANGEROUS!)"""
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
        for l in config.get("logins", []):
            if l["name"] == login:
                login_config = l
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


@gitea.command()
@click.argument("repository")
def fork(repository):
    """Fork a repository"""
    run_tea("repo", "fork", repository)


@gitea.group()
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


@gitea.group()
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


@gitea.command()
def push():
    """Push local changes to workspace"""
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
        click.echo("Pushing to workspace...")
        subprocess.run(["git", "push", "origin", branch], check=True)
        click.echo(f"Pushed to workspace (origin/{branch})")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@gitea.command()
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


@gitea.command()
def status():
    """Show repository status"""
    ensure_not_in_workspace()
    subprocess.run(["git", "status"])


@gitea.command()
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
    envvar="SCITEX_CLOUD_API_KEY",
    help="SciTeX API key (or set SCITEX_CLOUD_API_KEY)",
)
@click.option("--no-cache", is_flag=True, help="Disable cache")
@click.option("--url", default="https://scitex.cloud", help="SciTeX Cloud URL")
def enrich(input_file, output_file, api_key, no_cache, url):
    """Enrich BibTeX file with metadata"""
    import time

    import requests

    if not api_key:
        click.echo("Error: API key required", err=True)
        click.echo("Set SCITEX_CLOUD_API_KEY or use --api-key", err=True)
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
        status = data["status"]
        if status == "completed":
            click.echo(" Done!")
            break
        elif status in ("failed", "cancelled"):
            click.echo(f" {status.capitalize()}!", err=True)
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
