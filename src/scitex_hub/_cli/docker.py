#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/docker.py

"""Docker commands for scitex-hub CLI."""

import click

from .._config._environments import ENVIRONMENTS, get_environment
from .._utils._docker import DockerManager


@click.group()
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (dev, prod)",
)
@click.pass_context
def docker(ctx, env):
    """Docker container management.

    \b
    Manage Docker containers for SciTeX Cloud deployment.

    \b
    Examples:
        scitex-hub docker build        # Build containers
        scitex-hub docker up           # Start containers
        scitex-hub docker down         # Stop containers
        scitex-hub docker restart      # Restart containers
        scitex-hub docker ps           # Show container status
    """
    ctx.ensure_object(dict)
    ctx.obj["env"] = get_environment(env)
    ctx.obj["docker"] = DockerManager(ctx.obj["env"])


@docker.command()
@click.option("--no-cache", is_flag=True, help="Build without cache")
@click.pass_context
def build(ctx, no_cache):
    """Build Docker containers."""
    click.echo(click.style("Building containers...", fg="yellow"))
    returncode = ctx.obj["docker"].build(no_cache=no_cache)
    if returncode == 0:
        click.echo(click.style("Build complete", fg="green"))
    else:
        raise click.ClickException("Build failed")


@docker.command()
@click.option("-d", "--detach", is_flag=True, default=True, help="Run in background")
@click.pass_context
def up(ctx, detach):
    """Start Docker containers."""
    click.echo(click.style("Starting containers...", fg="yellow"))
    returncode = ctx.obj["docker"].up(detach=detach)
    if returncode == 0:
        env = ctx.obj["env"]
        click.echo(click.style("Containers started", fg="green"))
        click.echo(f"Running at: http://{env.host}:{env.port}")
    else:
        raise click.ClickException("Failed to start containers")


@docker.command()
@click.option("-v", "--volumes", is_flag=True, help="Remove volumes")
@click.pass_context
def down(ctx, volumes):
    """Stop Docker containers."""
    click.echo(click.style("Stopping containers...", fg="yellow"))
    returncode = ctx.obj["docker"].down(volumes=volumes)
    if returncode == 0:
        click.echo(click.style("Containers stopped", fg="green"))
    else:
        raise click.ClickException("Failed to stop containers")


@docker.command()
@click.pass_context
def restart(ctx):
    """Restart Docker containers."""
    click.echo(click.style("Restarting containers...", fg="yellow"))
    returncode = ctx.obj["docker"].restart()
    if returncode == 0:
        click.echo(click.style("Containers restarted", fg="green"))
    else:
        raise click.ClickException("Failed to restart containers")


@docker.command()
@click.pass_context
def ps(ctx):
    """Show container status."""
    ctx.obj["docker"].ps()


# EOF
