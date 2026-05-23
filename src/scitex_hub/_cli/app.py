#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI commands for SciTeX app init, validation, and development."""

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
@click.option(
    "--frontend",
    "-f",
    type=click.Choice(["html", "react"]),
    default="html",
    help="Frontend type: html (default) or react (React+Vite+Zustand)",
)
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
def app_init(target_dir, name, label, icon, description, frontend, overwrite):
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
    from scitex_hub.appmaker import validate

    errors = validate(app_dir)

    if not errors:
        console.print("[green]All checks passed![/green] App is ready for submission.")
    else:
        console.print(f"[red]Found {len(errors)} issue(s):[/red]")
        for error in errors:
            console.print(f"  [red]x[/red] {error}")
        raise SystemExit(1)


@app.command("install-dev")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8000, type=int, help="Dev server port")
def app_dev(app_dir, port):
    """Show instructions for local app development.

    \b
    Examples:
        scitex-cloud app dev .
        scitex-cloud app dev /path/to/my_app --port 8001
    """
    from scitex_hub.appmaker import dev_server

    dev_server(app_dir, port=port)


@app.command("submit")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_CLOUD_URL",
    default="http://127.0.0.1:8000",
    help="SciTeX Cloud server URL",
)
def app_submit(app_dir, server):
    """Validate and submit an app for publication review.

    Authenticates via JWT (prompts for credentials if needed),
    runs local validation, then submits to the server.
    A PR is opened on the central scitex/apps registry for review.
    Merge = approval (like MELPA).

    \b
    Examples:
        scitex-cloud app submit .
        scitex cloud app submit /path/to/my_app --server https://scitex.example.com
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


@app.command("list")
@click.option(
    "--server",
    "-s",
    envvar="SCITEX_CLOUD_URL",
    default="http://127.0.0.1:8000",
    help="SciTeX Cloud server URL",
)
def app_list(server):
    """List available apps.

    \b
    Examples:
        scitex-cloud app list
        scitex-cloud app list --server https://scitex.example.com
    """
    from scitex_hub.appmaker import list_all

    apps = list_all(server_url=server)
    if not apps:
        console.print("[yellow]No apps found.[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Apps")
    table.add_column("Name", style="cyan")
    table.add_column("Label")
    table.add_column("Order", justify="right")
    table.add_column("Description")

    for a in apps:
        table.add_row(
            a.get("name") or a.get("module_name", ""),
            a.get("label", ""),
            str(a.get("order", "")),
            (a.get("ai_hint") or a.get("short_description", ""))[:60],
        )

    console.print(table)


@app.command("show-current")
def app_current():
    """Show the currently active app.

    \b
    Examples:
        scitex-cloud app current
    """
    from scitex_hub.appmaker import get_current

    name = get_current()
    if name:
        console.print(f"[cyan]{name}[/cyan]")
    else:
        console.print("[yellow]No active app (SCITEX_CURRENT_APP not set)[/yellow]")


@app.command("switch")
@click.argument("app_name")
def app_switch(app_name):
    """Switch the active app.

    \b
    Examples:
        scitex-cloud app switch scholar
        scitex-cloud app switch writer
    """
    from scitex_hub.appmaker import switch_to

    switch_to(app_name)
    console.print(f"[green]Switched to:[/green] {app_name}")


@app.command("show-info")
@click.argument("app_name")
def app_info(app_name):
    """Show detailed info for an app.

    \b
    Examples:
        scitex-cloud app info writer
        scitex-cloud app info scholar
    """
    from scitex_hub.appmaker import get_info

    info = get_info(app_name)
    if not info:
        console.print(f"[red]App not found:[/red] {app_name}")
        raise SystemExit(1)

    for key, val in info.items():
        console.print(f"  [cyan]{key}:[/cyan] {val}")


@app.group("prefs")
def app_prefs():
    """Manage per-user app preferences."""


@app_prefs.command("get")
@click.argument("app_name")
def prefs_get(app_name):
    """Show preferences for an app.

    \b
    Examples:
        scitex-cloud app prefs get writer
    """
    from scitex_hub.appmaker import get_prefs

    prefs = get_prefs(app_name)
    if not prefs:
        console.print(f"[yellow]No preferences saved for {app_name}[/yellow]")
        return

    import json

    console.print(json.dumps(prefs, indent=2))


@app_prefs.command("set")
@click.argument("app_name")
@click.argument("key_values", nargs=-1)
def prefs_set(app_name, key_values):
    """Set preferences for an app as key=value pairs.

    \b
    Examples:
        scitex-cloud app prefs set writer theme=dark font_size=14
        scitex-cloud app prefs set scholar engine=crossref
    """
    from scitex_hub.appmaker import set_prefs

    prefs = {}
    for kv in key_values:
        if "=" not in kv:
            console.print(f"[red]Invalid format:[/red] {kv} (expected key=value)")
            raise SystemExit(1)
        key, val = kv.split("=", 1)
        # Try to parse as JSON for numeric/bool values
        try:
            import json

            prefs[key] = json.loads(val)
        except (json.JSONDecodeError, ValueError):
            prefs[key] = val

    set_prefs(app_name, prefs)
    console.print(f"[green]Saved preferences for {app_name}[/green]")


@app_prefs.command("delete")
@click.argument("app_name")
def prefs_delete(app_name):
    """Delete all preferences for an app.

    \b
    Examples:
        scitex-cloud app prefs delete writer
    """
    from scitex_hub.appmaker import delete_prefs

    if delete_prefs(app_name):
        console.print(f"[green]Deleted preferences for {app_name}[/green]")
    else:
        console.print(f"[yellow]No preferences found for {app_name}[/yellow]")


@app_prefs.command("list")
def prefs_list():
    """List all saved app preferences.

    \b
    Examples:
        scitex-cloud app prefs list
    """
    import json

    from scitex_hub.appmaker import list_prefs

    all_prefs = list_prefs()
    if not all_prefs:
        console.print("[yellow]No preferences saved[/yellow]")
        return

    console.print(json.dumps(all_prefs, indent=2))


@app.command("check-deps")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
def app_check_deps(app_dir):
    """Check app dependencies from manifest.json.

    \b
    Examples:
        scitex-cloud app check-deps .
        scitex-cloud app check-deps /path/to/my_app
    """
    from scitex_hub.appmaker import check_deps_from_manifest, format_missing_report

    manifest = Path(app_dir) / "manifest.json"
    if not manifest.is_file():
        console.print("[red]No manifest.json found[/red]")
        raise SystemExit(1)

    missing = check_deps_from_manifest(manifest)
    report = format_missing_report(missing)
    if missing:
        console.print(f"[yellow]{report}[/yellow]")
        raise SystemExit(1)
    else:
        console.print(f"[green]{report}[/green]")


@app.command("install-deps")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option(
    "--type",
    "-t",
    "dep_type",
    type=click.Choice(["python", "system", "node", "r"]),
    required=True,
    help="Dependency type to install",
)
def app_install_deps(app_dir, dep_type):
    """Install app dependencies of a specific type.

    \b
    Examples:
        scitex-cloud app install-deps . --type python
        scitex-cloud app install-deps . -t system
    """
    import json

    from scitex_hub.appmaker import install_deps

    manifest_path = Path(app_dir) / "manifest.json"
    if not manifest_path.is_file():
        console.print("[red]No manifest.json found[/red]")
        raise SystemExit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    console.print(f"[cyan]Installing {dep_type} dependencies...[/cyan]")

    result = install_deps(manifest, dep_type)

    if result["success"]:
        installed = result.get("installed", [])
        if installed:
            console.print(f"[green]Installed:[/green] {', '.join(installed)}")
        else:
            console.print("[green]No dependencies to install.[/green]")
    else:
        console.print(f"[red]Failed:[/red] {result['error']}")
        raise SystemExit(1)


@app.command("build-container")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    "output_dir",
    default=None,
    type=click.Path(),
    help="Output directory for .sif file",
)
def app_build_container(app_dir, output_dir):
    """Build an Apptainer container from an app's .def file.

    Reads the ``container`` field from manifest.json and builds a .sif image.

    \b
    Examples:
        scitex-cloud app build-container .
        scitex-cloud app build-container /path/to/my_app -o /data/containers/
    """
    from scitex_hub.appmaker import build_container

    out = Path(output_dir) if output_dir else None
    console.print(f"[cyan]Building container from:[/cyan] {Path(app_dir).resolve()}")

    result = build_container(Path(app_dir).resolve(), output_dir=out)

    if result["success"]:
        console.print(f"[green]Built:[/green] {result['sif_path']}")
    else:
        console.print(f"[red]Failed:[/red] {result['error']}")
        raise SystemExit(1)


# EOF
