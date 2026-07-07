#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/setup.py

"""Setup commands for scitex-hub CLI."""

import shutil
import sys
from pathlib import Path

import click

from .._config import load_config
from .._config._environments import ENVIRONMENTS, get_environment
from ._click_compat import spec_command_kwargs
from ._flags import confirm_or_abort, mutating_flags, print_dry_run


# Doctrine §1d: `setup` is banned; this leaf creates a brand-new
# environment-config skeleton (.env from template + compose check),
# which is exactly the `init` verb ("create a brand-new project/config
# skeleton where nothing existed"), not `install`.
@click.command(
    "init",
    **spec_command_kwargs(
        summary="Initialize the SciTeX Hub environment configuration.",
        description=(
            "Non-interactive init wizard: checks prerequisites, "
            "creates the environment file from the template, and "
            "validates the docker-compose file. Environment "
            "resolution: --env flag > SCITEX_HUB_ENV env var > config "
            "file `env` key; a missing value fails fast with exit "
            "code 2 (no prompt).",
        ),
        examples=(
            ("{prog} init --env dev", "Initialize the dev environment"),
            ("{prog} init --env prod", "Initialize the prod environment"),
            ("{prog} init --env dev --dry-run", "Preview without writing"),
            ("{prog} init --env prod --yes", "Skip confirmation"),
        ),
    ),
)
@click.option(
    "--env",
    type=click.Choice(list(ENVIRONMENTS.keys())),
    default=None,
    envvar="SCITEX_HUB_ENV",
    help="Target environment — dev, prod (env: SCITEX_HUB_ENV)",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@mutating_flags()
def setup(env, force, dry_run, yes):
    """Initialize the SciTeX Hub environment configuration.

    \b
    Non-interactive init wizard. Environment resolution (spec §6b):
    --env flag > SCITEX_HUB_ENV env var > config file `env` key.
    Missing value fails fast with exit code 2 — no prompt.

    \b
    Example:
        scitex-hub init --env dev          # Initialize development environment
        scitex-hub init --env prod         # Initialize production environment
        SCITEX_HUB_ENV=dev scitex-hub init
        scitex-hub init --env dev --dry-run
        scitex-hub init --env prod --yes
    """
    click.echo(click.style("SciTeX Hub Init", fg="cyan", bold=True))
    click.echo()

    if env is None:
        cfg = load_config()
        raw = cfg.get("env")
        if isinstance(raw, str):
            env = raw

    if env is None:
        click.echo(
            "error: set SCITEX_HUB_ENV or pass --env (choices: "
            f"{', '.join(ENVIRONMENTS.keys())})",
            err=True,
        )
        sys.exit(2)
    if env not in ENVIRONMENTS:
        click.echo(
            f"error: invalid --env '{env}' (choices: {', '.join(ENVIRONMENTS.keys())})",
            err=True,
        )
        sys.exit(2)

    environment = get_environment(env)

    if dry_run:
        print_dry_run(
            f"initialize environment '{environment.description}' (force={force})"
        )
        return

    confirm_or_abort(
        f"Initialize environment '{environment.description}' (force={force})?",
        yes=yes,
        dry_run=dry_run,
    )

    click.echo(f"Initializing: {click.style(environment.description, fg='green')}")
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
    click.echo(click.style("Init complete!", fg="green", bold=True))
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. Edit {environment.env_path} with your settings")
    click.echo(f"  2. Run: scitex-hub deploy --env {env}")


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
    return f"""# SciTeX Hub Environment Configuration
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
