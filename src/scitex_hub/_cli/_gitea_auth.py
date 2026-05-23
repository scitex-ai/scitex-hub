#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/_gitea_auth.py
"""Gitea CLI - Authentication commands (login / logout)."""

import sys

import click
import requests

from .._config import get_config_value
from ._gitea_utils import get_tea_config, run_tea

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_or_get_gitea_token(url, user, password):
    """Create a Gitea API token via Basic Auth, or surface a clear error.

    Returns the token string (sha1), or None on failure.
    """
    token_name = "scitex-cloud-cli"
    api_url = f"{url.rstrip('/')}/api/v1/users/{user}/tokens"
    auth = (user, password)

    # First attempt: with scopes (Gitea >= 1.19)
    response = requests.post(
        api_url,
        auth=auth,
        json={"name": token_name, "scopes": ["all"]},
        timeout=10,
    )

    if response.status_code == 201:
        click.echo(f"Created API token '{token_name}'")
        return response.json().get("sha1")

    if response.status_code == 409:
        # Token name already taken; list tokens to detect it
        click.echo(f"Token '{token_name}' already exists, looking it up...")
        list_resp = requests.get(api_url, auth=auth, timeout=10)
        if list_resp.status_code == 200:
            for entry in list_resp.json():
                if entry.get("name") == token_name:
                    click.echo(
                        f"Error: Token '{token_name}' exists but its value cannot be "
                        "retrieved via the API. Delete it on the Gitea web UI at "
                        f"{url.rstrip('/')}/user/settings/applications "
                        "then run login again.",
                        err=True,
                    )
                    return None
        click.echo("Error: Token conflict and could not list tokens.", err=True)
        return None

    if response.status_code == 401:
        click.echo("Error: Invalid username or password.", err=True)
        return None

    # Fallback: older Gitea without scopes support
    if response.status_code in (400, 422):
        response2 = requests.post(
            api_url,
            auth=auth,
            json={"name": token_name},
            timeout=10,
        )
        if response2.status_code == 201:
            click.echo(f"Created API token '{token_name}' (legacy mode)")
            return response2.json().get("sha1")

    click.echo(
        f"Error: Could not create API token (HTTP {response.status_code}): "
        f"{response.text}",
        err=True,
    )
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--url",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_URL",
    help="Gitea instance URL (auto-detected from .env; env: SCITEX_CLOUD_GITEA_URL)",
)
@click.option(
    "--token",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_TOKEN",
    help="API token, skip username/password flow (env: SCITEX_CLOUD_GITEA_TOKEN)",
)
@click.option(
    "--user",
    "-u",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_USER",
    help="Gitea username (env: SCITEX_CLOUD_GITEA_USER)",
)
@click.option(
    "--password",
    "-p",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_PASSWORD",
    help="Gitea password (env: SCITEX_CLOUD_GITEA_PASSWORD)",
)
@click.option(
    "--name", default="scitex-dev", help="Tea login name (default: scitex-dev)"
)
def login(url, token, user, password, name):
    """Login to SciTeX Cloud (Gitea).

    Non-interactive. Credentials resolve in precedence order (spec §6b):
    CLI flag → SCITEX_CLOUD_GITEA_{TOKEN,USER,PASSWORD} env var →
    config file. Missing credentials fail fast with exit code 2.

    Prefer --token (or SCITEX_CLOUD_GITEA_TOKEN) for unattended runs.
    Username+password still works when token unavailable.

    The Gitea URL is auto-detected from SCITEX_CLOUD_GITEA_URL_DEV env var
    or SECRET/.env.dev file. Override with --url.
    """
    from ._gitea_utils import get_gitea_url

    if url is None:
        url = get_gitea_url()
        click.echo(f"Auto-detected Gitea URL: {url}", err=True)

    if not token:
        user = user or get_config_value("gitea", "user")
        password = password or get_config_value("gitea", "password")

        if not user or not password:
            click.echo(
                "error: gitea credentials missing. Set "
                "SCITEX_CLOUD_GITEA_TOKEN (preferred) or "
                "SCITEX_CLOUD_GITEA_USER/SCITEX_CLOUD_GITEA_PASSWORD, "
                "or pass --token / --user and --password",
                err=True,
            )
            sys.exit(2)

        token = _create_or_get_gitea_token(url, user, password)
        if not token:
            sys.exit(1)

    args = ["login", "add", "--name", name, "--url", url, "--token", token]
    if user:
        args.extend(["--user", user])
    run_tea(*args)
    click.echo(f"Logged in to {url} as login '{name}'")


@click.command()
@click.option(
    "--name",
    default="scitex-dev",
    help="Tea login name to remove (default: scitex-dev)",
)
@click.option(
    "--url",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_URL",
    help="Gitea URL (env: SCITEX_CLOUD_GITEA_URL; needed when --delete-token is set)",
)
@click.option(
    "--user",
    "-u",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_USER",
    help="Gitea username (env: SCITEX_CLOUD_GITEA_USER; needed when --delete-token is set)",
)
@click.option(
    "--password",
    "-p",
    default=None,
    envvar="SCITEX_CLOUD_GITEA_PASSWORD",
    help="Gitea password (env: SCITEX_CLOUD_GITEA_PASSWORD; needed when --delete-token is set)",
)
@click.option(
    "--delete-token",
    is_flag=True,
    help="Also delete the API token from the Gitea server",
)
def logout(name, url, user, password, delete_token):
    """Logout from SciTeX Cloud (Gitea).

    Removes the local tea login entry.  Use --delete-token to also revoke
    the API token on the Gitea server. In that mode, password is required
    non-interactively via --password or SCITEX_CLOUD_GITEA_PASSWORD
    (fail-fast with exit code 2 if missing — no prompt, spec §2).
    """
    if delete_token:
        # Try to pull connection details from tea config if not given
        if not url or not user:
            try:
                cfg = get_tea_config(name)
                url = url or cfg.get("url", "")
                user = user or cfg.get("user", "")
            except SystemExit:
                pass

        if not url or not user:
            click.echo(
                "Error: --url and --user are required with --delete-token", err=True
            )
            sys.exit(2)

        if not password:
            password = get_config_value("gitea", "password")
        if not password:
            click.echo(
                "error: --delete-token requires a password. Set "
                "SCITEX_CLOUD_GITEA_PASSWORD or pass --password",
                err=True,
            )
            sys.exit(2)

        token_name = "scitex-cloud-cli"
        api_url = f"{url.rstrip('/')}/api/v1/users/{user}/tokens"
        auth = (user, password)

        list_resp = requests.get(api_url, auth=auth, timeout=10)
        if list_resp.status_code == 200:
            for entry in list_resp.json():
                if entry.get("name") == token_name:
                    del_resp = requests.delete(
                        f"{api_url}/{entry['id']}", auth=auth, timeout=10
                    )
                    if del_resp.status_code == 204:
                        click.echo(f"Deleted API token '{token_name}' from {url}")
                    else:
                        click.echo(
                            f"Warning: Could not delete token "
                            f"(HTTP {del_resp.status_code})",
                            err=True,
                        )
                    break
            else:
                click.echo(
                    f"Token '{token_name}' not found on server (already deleted?)"
                )
        else:
            click.echo(
                f"Warning: Could not list tokens (HTTP {list_resp.status_code})",
                err=True,
            )

    run_tea("login", "delete", "--name", name)
    click.echo(f"Removed tea login '{name}'")


# EOF
