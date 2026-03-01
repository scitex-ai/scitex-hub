#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI commands for SciTeX app scaffold, validation, and development."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
def app():
    """Manage SciTeX app plugins."""


@app.command("init")
@click.argument("target_dir", default=".", type=click.Path())
@click.option("--name", "-n", default=None, help="App module name (must end with _app)")
@click.option("--label", "-l", default=None, help="Human-readable label")
@click.option(
    "--icon", "-i", default="fas fa-puzzle-piece", help="Font Awesome icon class"
)
@click.option("--description", "-d", default="", help="Short description")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
def app_init(target_dir, name, label, icon, description, overwrite):
    """Scaffold a complete SciTeX app in a directory.

    Creates all required boilerplate files: apps.py, views.py, urls.py,
    tests.py, skill.py, manifest.json, templates, static, agents config,
    README, and LICENSE.

    \b
    Examples:
        scitex-cloud app init .
        scitex-cloud app init /path/to/my_app --name my_awesome_app
        scitex-cloud app init . -n demo_app -l "Demo" -i "fas fa-flask"
    """
    from scitex_cloud.app_tools import scaffold

    target = Path(target_dir).resolve()
    app_name = name or target.name

    if not (app_name.endswith("_app") or app_name.endswith("-app")):
        sep = "-" if "-" in app_name else "_"
        suffixed = f"{app_name}{sep}app"
        console.print(
            f"[yellow]Warning:[/yellow] App name '{app_name}' does not end with "
            f"'_app' or '-app'. Adding suffix: '{suffixed}'"
        )
        app_name = suffixed

    console.print(f"[cyan]Scaffolding app:[/cyan] {app_name} in {target}")

    created = scaffold(
        target_dir=target,
        name=app_name,
        label=label or "",
        icon=icon,
        description=description,
        overwrite=overwrite,
    )

    for filepath in created:
        console.print(f"  [green]+[/green] {filepath}")

    if not created:
        console.print("  [yellow]No new files created (all already exist).[/yellow]")
    else:
        console.print(f"\n[green]Done![/green] Created {len(created)} files.")


@app.command("validate")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
def app_validate(app_dir):
    """Validate a SciTeX app for submission readiness.

    Checks structure, security, and manifest compliance.

    \b
    Examples:
        scitex-cloud app validate .
        scitex-cloud app validate /path/to/my_app
    """
    from scitex_cloud.app_tools import validate

    errors = validate(app_dir)

    if not errors:
        console.print("[green]All checks passed![/green] App is ready for submission.")
    else:
        console.print(f"[red]Found {len(errors)} issue(s):[/red]")
        for error in errors:
            console.print(f"  [red]x[/red] {error}")
        raise SystemExit(1)


@app.command("dev")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8000, type=int, help="Dev server port")
def app_dev(app_dir, port):
    """Show instructions for local app development.

    \b
    Examples:
        scitex-cloud app dev .
        scitex-cloud app dev /path/to/my_app --port 8001
    """
    from scitex_cloud.app_tools import dev_server

    dev_server(app_dir, port=port)


# EOF
