#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/status.py

"""Status and logs commands for scitex-hub CLI."""

import click

from .._config._environments import ENVIRONMENTS, get_environment
from .._utils._docker import DockerManager
from ._flags import emit_json, json_flag


@click.command()
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (dev, prod)",
)
@json_flag()
def status(env, json_output):
    """Show deployment status.

    \b
    Display current status of SciTeX Hub deployment including
    container states, resource usage, and service health.

    \b
    Example:
        scitex-hub show-status                  # Show current status
        scitex-hub show-status --env prod       # Show production deployment status
        scitex-hub show-status --json           # Emit machine-readable JSON
    """
    environment = get_environment(env)
    docker = DockerManager(environment)

    if json_output:
        emit_json(
            {
                "success": True,
                "environment": environment.name,
                "description": environment.description,
                "url": f"http://{environment.host}:{environment.port}",
            }
        )
        # Still surface raw container state via docker.ps() for parity,
        # but only the JSON header is the canonical machine payload —
        # downstream consumers should rely on the JSON above.
        return

    click.echo(
        click.style(
            f"SciTeX Hub Status: {environment.description}", fg="cyan", bold=True
        )
    )
    click.echo()

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
@json_flag()
def logs(env, follow, tail, service, json_output):
    """Show container logs.

    \b
    Display logs from SciTeX Hub containers. Default streams the raw
    unstructured log text from `docker logs`. With ``--json`` a single
    envelope describing the query is emitted instead — useful for
    scripts that just want to record what was requested, since the
    underlying stream is not itself structured.

    \b
    Example:
        scitex-hub show-logs                  # Show all logs
        scitex-hub show-logs -f               # Follow logs
        scitex-hub show-logs --tail 100       # Show last 100 lines
        scitex-hub show-logs web              # Show web container logs
        scitex-hub show-logs --json           # Emit machine-readable envelope
    """
    environment = get_environment(env)
    if json_output:
        emit_json(
            {
                "success": True,
                "environment": environment.name,
                "service": service,
                "follow": bool(follow),
                "tail": tail,
            }
        )
        return
    docker = DockerManager(environment)
    docker.logs(follow=follow, tail=tail, service=service)


# EOF
