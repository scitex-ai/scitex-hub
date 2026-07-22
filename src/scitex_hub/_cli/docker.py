#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/docker.py

"""Docker commands for scitex-hub CLI.

All mutating verbs (``build``, ``up``, ``down``, ``restart``) honour
``--dry-run`` (print the plan, return without invoking docker) and ``-y/--yes``
(skip the confirmation prompt on a TTY). The read verb ``ps`` exposes
``--json`` per §2 universal-flag conventions.
"""

import click

from .._config._environments import ENVIRONMENTS, get_environment
from .._utils._docker import DockerManager
from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._flags import (
    confirm_or_abort,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
)


@click.group(
    **spec_group_kwargs(
        summary="Docker container management for the hub deployment."
    )
)
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
    Manage Docker containers for SciTeX Hub deployment.

    \b
    Example:
        scitex-hub docker build        # Build containers
        scitex-hub docker up           # Start containers
        scitex-hub docker down         # Stop containers
        scitex-hub docker restart      # Restart containers
        scitex-hub docker ps           # Show container status
    """
    ctx.ensure_object(dict)
    ctx.obj["env"] = get_environment(env)
    ctx.obj["docker"] = DockerManager(ctx.obj["env"])


@docker.command(
    **spec_command_kwargs(
        summary="Build Docker containers.",
        examples=(("{prog} docker build --yes", "Build containers."),),
    )
)
@click.option("--no-cache", is_flag=True, help="Build without cache")
@mutating_flags()
@click.pass_context
def build(ctx, no_cache, dry_run, yes):
    """Build Docker containers.

    \b
    Example:
        scitex-hub docker build
        scitex-hub docker build --no-cache --yes
    """
    if dry_run:
        print_dry_run(
            f"would build Docker containers for env "
            f"{ctx.obj['env'].name!r} (no_cache={no_cache})"
        )
        return

    confirm_or_abort(
        f"Build Docker containers for env {ctx.obj['env'].name!r}?",
        yes=yes,
        dry_run=dry_run,
    )

    click.echo(click.style("Building containers...", fg="yellow"))
    returncode = ctx.obj["docker"].build(no_cache=no_cache)
    if returncode == 0:
        click.echo(click.style("Build complete", fg="green"))
    else:
        raise click.ClickException("Build failed")


@docker.command(
    **spec_command_kwargs(
        summary="Start Docker containers.",
        examples=(("{prog} docker up --yes", "Start containers."),),
    )
)
@click.option("-d", "--detach", is_flag=True, default=True, help="Run in background")
@mutating_flags()
@click.pass_context
def up(ctx, detach, dry_run, yes):
    """Start Docker containers.

    \b
    Example:
        scitex-hub docker up
        scitex-hub docker up --yes
    """
    if dry_run:
        print_dry_run(
            f"would start Docker containers for env "
            f"{ctx.obj['env'].name!r} (detach={detach})"
        )
        return

    confirm_or_abort(
        f"Start Docker containers for env {ctx.obj['env'].name!r}?",
        yes=yes,
        dry_run=dry_run,
    )

    click.echo(click.style("Starting containers...", fg="yellow"))
    returncode = ctx.obj["docker"].up(detach=detach)
    if returncode == 0:
        env = ctx.obj["env"]
        click.echo(click.style("Containers started", fg="green"))
        click.echo(f"Running at: http://{env.host}:{env.port}")
    else:
        raise click.ClickException("Failed to start containers")


@docker.command(
    **spec_command_kwargs(
        summary="Stop Docker containers.",
        examples=(("{prog} docker down --yes", "Stop containers."),),
    )
)
@click.option("-v", "--volumes", is_flag=True, help="Remove volumes")
@mutating_flags()
@click.pass_context
def down(ctx, volumes, dry_run, yes):
    """Stop Docker containers.

    \b
    Example:
        scitex-hub docker down
        scitex-hub docker down --volumes --yes
    """
    if dry_run:
        print_dry_run(
            f"would stop Docker containers for env "
            f"{ctx.obj['env'].name!r} (remove_volumes={volumes})"
        )
        return

    confirm_or_abort(
        f"Stop Docker containers for env {ctx.obj['env'].name!r}?",
        yes=yes,
        dry_run=dry_run,
    )

    click.echo(click.style("Stopping containers...", fg="yellow"))
    returncode = ctx.obj["docker"].down(volumes=volumes)
    if returncode == 0:
        click.echo(click.style("Containers stopped", fg="green"))
    else:
        raise click.ClickException("Failed to stop containers")


@docker.command(
    **spec_command_kwargs(
        summary="Restart Docker containers.",
        examples=(("{prog} docker restart --yes", "Restart containers."),),
    )
)
@mutating_flags()
@click.pass_context
def restart(ctx, dry_run, yes):
    """Restart Docker containers.

    \b
    Example:
        scitex-hub docker restart
        scitex-hub docker restart --yes
    """
    if dry_run:
        print_dry_run(
            f"would restart Docker containers for env {ctx.obj['env'].name!r}"
        )
        return

    confirm_or_abort(
        f"Restart Docker containers for env {ctx.obj['env'].name!r}?",
        yes=yes,
        dry_run=dry_run,
    )

    click.echo(click.style("Restarting containers...", fg="yellow"))
    returncode = ctx.obj["docker"].restart()
    if returncode == 0:
        click.echo(click.style("Containers restarted", fg="green"))
    else:
        raise click.ClickException("Failed to restart containers")


@docker.command(
    **spec_command_kwargs(
        summary="Show container status.",
        examples=(("{prog} docker ps", "Show container status."),),
    )
)
@json_flag()
@click.pass_context
def ps(ctx, json_output):
    """Show container status.

    With ``--json``, emits a structured snapshot of the target env. The
    human-readable docker-compose ps table is still used by default.

    \b
    Example:
        scitex-hub docker ps
        scitex-hub docker ps --json
    """
    if json_output:
        env = ctx.obj["env"]
        payload = {
            "env": getattr(env, "name", str(env)),
            "host": getattr(env, "host", None),
            "port": getattr(env, "port", None),
        }
        if hasattr(ctx.obj["docker"], "ps_json"):
            payload["containers"] = ctx.obj["docker"].ps_json()
        emit_json(payload)
        return
    ctx.obj["docker"].ps()


# EOF
