#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/project.py
"""Project CRUD CLI commands."""

import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _require_yes(yes, action):
    """Fail fast with exit 2 if destructive action lacks --yes (spec §2)."""
    if not yes:
        click.echo(
            f"error: pass --yes/-y to confirm destructive action: {action}",
            err=True,
        )
        sys.exit(2)


@click.group()
def project():
    """Manage SciTeX Hub projects.

    \b
    Examples:
        scitex-hub project list
        scitex-hub project create my-research --description "Paper on X"
        scitex-hub project delete my-research --yes
        scitex-hub project rename my-research new-name
    """


@project.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def project_list(as_json):
    """List all your projects."""
    from scitex_hub.project import project_list as _list

    try:
        projects = _list()
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)

    if as_json:
        import json

        click.echo(json.dumps(projects, indent=2, default=str))
        return

    if not projects:
        console.print("[yellow]No projects found.[/yellow]")
        return

    table = Table(title="Projects")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Created")
    for p in projects:
        table.add_row(
            p.get("name", ""),
            p.get("description", ""),
            str(p.get("created_at", ""))[:10],
        )
    console.print(table)


@project.command("create")
@click.argument("name")
@click.option("-d", "--description", default="", help="Project description")
@click.option("-t", "--template", default="scitex_minimal", help="Template ID")
def project_create(name, description, template):
    """Create a new project."""
    from scitex_hub.project import project_create as _create

    try:
        result = _create(name, description=description, template=template)
        console.print(f"[green]Created project: {result.get('message', name)}[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@project.command("delete")
@click.argument("slug")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Confirm destructive action (required for non-interactive use)",
)
def project_delete(slug, yes):
    """Delete a project by slug. Requires --yes/-y (no interactive prompt)."""
    _require_yes(yes, f"delete project '{slug}'")

    from scitex_hub.project import project_delete as _delete

    try:
        _delete(slug)
        console.print(f"[green]Deleted project: {slug}[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@project.command("rename")
@click.argument("slug")
@click.argument("new_name")
def project_rename(slug, new_name):
    """Rename a project."""
    from scitex_hub.project import project_rename as _rename

    try:
        result = _rename(slug, new_name)
        console.print(f"[green]Renamed '{slug}' to '{new_name}'[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# EOF
