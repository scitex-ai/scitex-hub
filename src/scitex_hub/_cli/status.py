#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/status.py

"""Status and logs commands for scitex-hub CLI."""

import click

from .._config._environments import ENVIRONMENTS, get_environment
from .._utils._docker import DockerManager


@click.command()
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (dev, prod)",
)
@click.pass_context
def status(ctx, env):
    """Show deployment status.

    \b
    Display current status of SciTeX Hub deployment including
    container states, resource usage, and service health.

    \b
    Examples:
        scitex-hub status              # Show current status
        scitex-hub status --env prod   # Show production deployment status
    """
    environment = get_environment(env)
    click.echo(
        click.style(
            f"SciTeX Hub Status: {environment.description}", fg="cyan", bold=True
        )
    )
    click.echo()

    docker = DockerManager(environment)

    click.echo(click.style("Container Status:", fg="yellow"))
    docker.ps()

    click.echo()
    click.echo(f"Environment: {environment.name}")
    click.echo(f"URL: http://{environment.host}:{environment.port}")


@click.command()
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (dev, prod)",
)
@click.option("-f", "--follow", is_flag=True, help="Follow log output")
@click.option("--tail", type=int, default=None, help="Number of lines to show")
@click.argument("service", required=False)
@click.pass_context
def logs(ctx, env, follow, tail, service):
    """Show container logs.

    \b
    Display logs from SciTeX Hub containers.

    \b
    Examples:
        scitex-hub logs                # Show all logs
        scitex-hub logs -f             # Follow logs
        scitex-hub logs --tail 100     # Show last 100 lines
        scitex-hub logs web            # Show web container logs
    """
    environment = get_environment(env)
    docker = DockerManager(environment)
    docker.logs(follow=follow, tail=tail, service=service)


# EOF
