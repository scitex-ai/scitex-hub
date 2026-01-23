#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/deploy.py

"""Deploy commands for scitex-cloud CLI."""

from pathlib import Path

import click

from ..config.environments import ENVIRONMENTS, get_environment
from ..utils.docker import DockerManager


@click.command()
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (dev, nas)",
)
@click.option("--build", is_flag=True, help="Rebuild containers before deploying")
@click.option("--no-cache", is_flag=True, help="Build without cache")
@click.pass_context
def deploy(ctx, env, build, no_cache):
    """Deploy SciTeX Cloud.

    \b
    Deploy or update SciTeX Cloud containers for the specified environment.
    Automatically handles configuration and container orchestration.

    \b
    Examples:
        scitex-cloud deploy              # Deploy with current settings
        scitex-cloud deploy --env nas    # Deploy to NAS environment
        scitex-cloud deploy --build      # Rebuild and deploy
    """
    environment = get_environment(env)
    click.echo(
        click.style(f"Deploying: {environment.description}", fg="cyan", bold=True)
    )
    click.echo()

    # Validate configuration
    _validate_deployment(environment)

    docker = DockerManager(environment)

    # Build if requested
    if build:
        click.echo(click.style("Building containers...", fg="yellow"))
        returncode = docker.build(no_cache=no_cache)
        if returncode != 0:
            raise click.ClickException("Build failed")
        click.echo(click.style("Build complete", fg="green"))
        click.echo()

    # Start containers
    click.echo(click.style("Starting containers...", fg="yellow"))
    returncode = docker.up(detach=True)
    if returncode != 0:
        raise click.ClickException("Failed to start containers")

    click.echo()
    click.echo(click.style("Deployment complete!", fg="green", bold=True))
    click.echo()
    click.echo(
        f"SciTeX Cloud is running at: http://{environment.host}:{environment.port}"
    )
    click.echo()
    click.echo("Useful commands:")
    click.echo("  scitex-cloud status    # Check container status")
    click.echo("  scitex-cloud logs -f   # Follow logs")
    click.echo("  scitex-cloud docker down  # Stop containers")


def _validate_deployment(environment):
    """Validate deployment configuration."""
    env_path = Path(environment.env_path)
    compose_path = Path(environment.compose_path)

    errors = []

    if not env_path.exists():
        errors.append(f"Environment file not found: {env_path}")

    if not compose_path.exists():
        errors.append(f"Docker compose file not found: {compose_path}")

    if errors:
        click.echo(click.style("Validation errors:", fg="red"))
        for error in errors:
            click.echo(f"  - {error}")
        click.echo()
        click.echo("Run 'scitex-cloud setup' to configure the environment.")
        raise click.ClickException("Deployment validation failed")

    click.echo(f"  {click.style('✓', fg='green')} Configuration validated")


# EOF
