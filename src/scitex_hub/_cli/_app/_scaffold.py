#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``app init`` / ``app install-dev`` / ``app submit`` / ``app validate`` /
``app switch`` verbs.

These all "set up" or "transition" an app in some way; grouping them keeps
each file focused while staying well under the 512-line cap.
"""

from __future__ import annotations

from pathlib import Path

import click

from .._flags import confirm_or_abort, mutating_flags, print_dry_run
from ._group import app, console


@app.command("init")
@click.argument("target_dir", default=".", type=click.Path())
@click.option("--name", "-n", default=None, help="App module name (must end with _app)")
@click.option("--label", "-l", default=None, help="Human-readable label")
@click.option(
    "--icon", "-i", default="fas fa-puzzle-piece", help="Font Awesome icon class"
)
@click.option("--description", "-d", default="", help="Short description")
@click.option(
    "--frontend",
    "-f",
    type=click.Choice(["html", "react"]),
    default="html",
    help="Frontend type: html (default) or react (React+Vite+Zustand)",
)
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
@mutating_flags()
def app_init(
    target_dir, name, label, icon, description, frontend, overwrite, dry_run, yes
) -> None:
    """Scaffold a complete SciTeX app in a directory.

    Creates all required boilerplate files: apps.py, views.py, urls.py,
    tests.py, skill.py, manifest.json, templates, static, agents config,
    README, and LICENSE.

    \b
    Example:
        scitex-hub app init .
        scitex-hub app init /path/to/my_app --name my_awesome_app
        scitex-hub app init . -n demo_app -l "Demo" -i "fas fa-flask"
    """
    target = Path(target_dir).resolve()
    app_name = name or target.name

    if dry_run:
        print_dry_run(
            f"would scaffold app '{app_name}' in {target} "
            f"(frontend={frontend}, overwrite={overwrite})"
        )
        return

    confirm_or_abort(
        f"Scaffold app '{app_name}' in {target}?", yes=yes, dry_run=dry_run
    )

    if not (app_name.endswith("_app") or app_name.endswith("-app")):
        sep = "-" if "-" in app_name else "_"
        suffixed = f"{app_name}{sep}app"
        console.print(
            f"[yellow]Warning:[/yellow] App name '{app_name}' does not end with "
            f"'_app' or '-app'. Adding suffix: '{suffixed}'"
        )
        app_name = suffixed

    console.print(f"[cyan]Scaffolding app:[/cyan] {app_name} in {target}")

    from scitex_hub.appmaker import init_app

    created = init_app(
        target_dir=target,
        name=app_name,
        label=label or "",
        icon=icon,
        description=description,
        overwrite=overwrite,
        frontend_type=frontend,
    )

    for filepath in created:
        console.print(f"  [green]+[/green] {filepath}")

    if not created:
        console.print("  [yellow]No new files created (all already exist).[/yellow]")
    else:
        console.print(f"\n[green]Done![/green] Created {len(created)} files.")


@app.command("install-dev")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8000, type=int, help="Dev server port")
@mutating_flags()
def app_dev(app_dir, port, dry_run, yes) -> None:
    """Show instructions for local app development.

    \b
    Example:
        scitex-hub app install-dev .
        scitex-hub app install-dev /path/to/my_app --port 8001
    """
    if dry_run:
        print_dry_run(
            f"would print dev-server instructions for {app_dir} on port {port}"
        )
        return

    confirm_or_abort(
        f"Print dev-server instructions for {app_dir}?", yes=yes, dry_run=dry_run
    )

    from scitex_hub.appmaker import dev_server

    dev_server(app_dir, port=port)


@app.command("validate")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
def app_validate(app_dir) -> None:
    """Validate a SciTeX app for submission readiness.

    Checks structure, security, and manifest compliance.

    \b
    Example:
        scitex-hub app validate .
        scitex-hub app validate /path/to/my_app
    """
    from scitex_hub.appmaker import validate

    errors = validate(app_dir)

    if not errors:
        console.print("[green]All checks passed![/green] App is ready for submission.")
    else:
        console.print(f"[red]Found {len(errors)} issue(s):[/red]")
        for error in errors:
            console.print(f"  [red]x[/red] {error}")
        raise SystemExit(1)


@app.command("submit")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_HUB_URL",
    default="http://127.0.0.1:8000",
    help="SciTeX Hub server URL",
)
def app_submit(app_dir, server) -> None:
    """Validate and submit an app for publication review.

    Authenticates via JWT (prompts for credentials if needed),
    runs local validation, then submits to the server.
    A PR is opened on the central scitex/apps registry for review.
    Merge = approval (like MELPA).

    \b
    Example:
        scitex-hub app submit .
        scitex-hub app submit /path/to/my_app --server https://scitex.example.com
    """
    from scitex_hub._cli._workspace_auth import get_jwt_token, get_server_url
    from scitex_hub.appmaker import publish

    server_url = get_server_url(server)
    token = get_jwt_token(server_url)

    console.print(f"[cyan]Submitting app from:[/cyan] {Path(app_dir).resolve()}")

    result = publish(app_dir, server_url=server_url, token=token)

    if result.get("success"):
        console.print("[green]Submitted for review![/green]")
        pr_url = result.get("pr_url", "")
        if pr_url:
            console.print(f"[cyan]Registry PR:[/cyan] {pr_url}")
    else:
        errors = result.get("errors", [result.get("error", "Unknown error")])
        console.print("[red]Failed:[/red]")
        for err in errors:
            console.print(f"  [red]x[/red] {err}")
        raise SystemExit(1)


@app.command("switch")
@click.argument("app_name")
def app_switch(app_name) -> None:
    """Switch the active app.

    \b
    Example:
        scitex-hub app switch scholar
        scitex-hub app switch writer
    """
    from scitex_hub.appmaker import switch_to

    switch_to(app_name)
    console.print(f"[green]Switched to:[/green] {app_name}")


# EOF
