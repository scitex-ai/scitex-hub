#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/ssh.py

"""SSH commands for connecting to SciTeX Hub instances."""

import os
import subprocess
import sys

import click

from .._config._environments import ENVIRONMENTS, get_environment

# SSH port per environment (maps to Docker-exposed port 2200)
SSH_PORTS = {
    "dev": 2200,
    "prod": 22,  # Cloudflare tunnel handles routing
}

SSH_HOSTS = {
    "dev": "127.0.0.1",
    "prod": "ssh.scitex.ai",
}


@click.command()
@click.option(
    "--env",
    "env_name",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (default: auto-detect)",
)
@click.option(
    "--user",
    "-u",
    "username",
    default=None,
    help="SSH username (default: current OS user)",
)
@click.option(
    "--port",
    "-p",
    "port",
    type=int,
    default=None,
    help="SSH port (default: env-specific)",
)
@click.argument("ssh_args", nargs=-1, type=click.UNPROCESSED)
def ssh(env_name, username, port, ssh_args):
    """SSH into a SciTeX Hub instance.

    \b
    Examples:
        scitex-hub ssh                    # SSH to default env
        scitex-hub ssh --env dev          # SSH to dev (127.0.0.1:2200)
        scitex-hub ssh --env prod         # SSH to production
        scitex-hub ssh -u myuser          # SSH as specific user
        scitex-hub ssh -- -L 8888:localhost:8888  # With port forwarding
    """
    env = get_environment(env_name)
    host = SSH_HOSTS.get(env.name, "127.0.0.1")
    ssh_port = port or SSH_PORTS.get(env.name, 2200)
    user = username or os.environ.get("USER", os.environ.get("USERNAME", ""))

    if not user:
        click.secho("Cannot determine username. Use --user.", fg="red", err=True)
        sys.exit(1)

    cmd = ["ssh", "-p", str(ssh_port)]
    # Add extra args passed after --
    cmd.extend(ssh_args)
    cmd.append(f"{user}@{host}")

    click.echo(f"Connecting to {host}:{ssh_port} as {user}...")
    os.execvp("ssh", cmd)


@click.command("ssh-copy-id")
@click.option(
    "--env",
    "env_name",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (default: auto-detect)",
)
@click.option(
    "--user",
    "-u",
    "username",
    default=None,
    help="SSH username (default: current OS user)",
)
@click.option(
    "--port",
    "-p",
    "port",
    type=int,
    default=None,
    help="SSH port (default: env-specific)",
)
@click.option(
    "--identity",
    "-i",
    "identity_file",
    default=None,
    help="Identity file to copy (default: ssh-copy-id default)",
)
def ssh_copy_id(env_name, username, port, identity_file):
    """Register your SSH key with a SciTeX Hub instance.

    \b
    Examples:
        scitex-hub ssh-copy-id                    # Register default key
        scitex-hub ssh-copy-id --env dev          # Register with dev instance
        scitex-hub ssh-copy-id -i ~/.ssh/id_ed25519.pub  # Specific key
    """
    env = get_environment(env_name)
    host = SSH_HOSTS.get(env.name, "127.0.0.1")
    ssh_port = port or SSH_PORTS.get(env.name, 2200)
    user = username or os.environ.get("USER", os.environ.get("USERNAME", ""))

    if not user:
        click.secho("Cannot determine username. Use --user.", fg="red", err=True)
        sys.exit(1)

    cmd = ["ssh-copy-id", "-p", str(ssh_port)]
    if identity_file:
        cmd.extend(["-i", identity_file])
    cmd.append(f"{user}@{host}")

    click.echo(f"Registering SSH key with {host}:{ssh_port} as {user}...")
    sys.exit(subprocess.call(cmd))


# EOF
