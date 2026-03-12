#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/setup.py

"""Setup commands for scitex-cloud CLI."""

import shutil
from pathlib import Path

import click

from .._config._environments import ENVIRONMENTS, get_environment


@click.command()
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    help="Target environment (dev, prod)",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def setup(ctx, env, force):
    """Setup SciTeX Cloud environment.

    \b
    Interactive setup wizard for configuring SciTeX Cloud deployment.
    Creates necessary configuration files and validates prerequisites.

    \b
    Examples:
        scitex-cloud setup              # Interactive setup
        scitex-cloud setup --env dev    # Setup development environment
        scitex-cloud setup --env prod   # Setup production environment
    """
    click.echo(click.style("SciTeX Cloud Setup", fg="cyan", bold=True))
    click.echo()

    # Select environment
    if env is None:
        env = click.prompt(
            "Select environment",
            type=click.Choice(list(ENVIRONMENTS.keys())),
            default="dev",
        )

    environment = get_environment(env)
    click.echo(f"Setting up: {click.style(environment.description, fg='green')}")
    click.echo()

    # Check prerequisites
    click.echo(click.style("Checking prerequisites...", fg="yellow"))
    _check_prerequisites()

    # Check/create env file
    click.echo(click.style("Checking configuration files...", fg="yellow"))
    _setup_env_file(environment, force)

    # Check docker-compose file
    _check_compose_file(environment)

    click.echo()
    click.echo(click.style("Setup complete!", fg="green", bold=True))
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. Edit {environment.env_path} with your settings")
    click.echo(f"  2. Run: scitex-cloud deploy --env {env}")


def _check_prerequisites():
    """Check required tools are installed."""
    tools = ["docker", "git"]
    missing = []

    for tool in tools:
        if not shutil.which(tool):
            missing.append(tool)
            click.echo(f"  {click.style('x', fg='red')} {tool} not found")
        else:
            click.echo(f"  {click.style('✓', fg='green')} {tool} found")

    if missing:
        raise click.ClickException(f"Missing required tools: {', '.join(missing)}")


def _setup_env_file(environment, force):
    """Setup environment file."""
    env_path = Path(environment.env_path)
    template_path = Path("deployment/docker/envs/.env.example")

    if env_path.exists() and not force:
        click.echo(f"  {click.style('✓', fg='green')} {env_path} exists")
        return

    if template_path.exists():
        shutil.copy(template_path, env_path)
        click.echo(f"  {click.style('✓', fg='green')} Created {env_path} from template")
    else:
        click.echo(
            f"  {click.style('!', fg='yellow')} Template not found, creating minimal {env_path}"
        )
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(_get_minimal_env_content(environment))
        click.echo(f"  {click.style('✓', fg='green')} Created {env_path}")


def _check_compose_file(environment):
    """Check docker-compose file exists."""
    compose_path = Path(environment.compose_path)
    if compose_path.exists():
        click.echo(f"  {click.style('✓', fg='green')} {compose_path} exists")
    else:
        click.echo(f"  {click.style('x', fg='red')} {compose_path} not found")
        raise click.ClickException(f"Docker compose file not found: {compose_path}")


def _get_minimal_env_content(environment):
    """Generate minimal .env file content."""
    return f"""# SciTeX Cloud Environment Configuration
# Environment: {environment.name}

# Django Settings
DEBUG={"True" if environment.name == "dev" else "False"}
SECRET_KEY=change-me-to-a-secure-random-string
ALLOWED_HOSTS={environment.host}

# Database
POSTGRES_DB=scitex
POSTGRES_USER=scitex
POSTGRES_PASSWORD=change-me

# Redis
REDIS_URL=redis://redis:6379/0
"""


# EOF
