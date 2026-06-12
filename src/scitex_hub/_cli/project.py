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
@click.option(
    "-c",
    "--category",
    type=click.Choice(["project", "app"], case_sensitive=False),
    default="project",
    show_default=True,
    help=(
        "Top-level project category. 'app' marks the project as an app "
        "plugin (is_app=True) and auto-suffixes the name with '_app' if "
        "missing — does NOT submit it to the registry."
    ),
)
@click.option(
    "--app",
    "app_shorthand",
    is_flag=True,
    help="Shorthand for --category app. Mutually exclusive with --category=app already-set.",
)
@click.option(
    "--app-category",
    "app_category",
    type=click.Choice(
        [
            "writing",
            "visualization",
            "data",
            "analysis",
            "reference",
            "utility",
            "other",
        ],
        case_sensitive=False,
    ),
    default=None,
    help=(
        "App sub-category for marketplace listing. Only valid with "
        "--category app (or --app). Optional at create time — can also be "
        "filled in at `app submit`."
    ),
)
def project_create(name, description, template, category, app_shorthand, app_category):
    """Create a new project.

    \b
    Examples:
        # Research project (default)
        scitex-hub project create my-research --description "..."

        # App project — auto-suffixes to my-tool_app
        scitex-hub project create my-tool --category app
        scitex-hub project create my-tool --app          # shorthand

        # App project with pre-set sub-category
        scitex-hub project create my-tool --app --app-category writing
    """
    from scitex_hub.project import project_create as _create

    # Resolve --app shorthand and reject the conflicting combo.
    if app_shorthand:
        if category != "project":
            console.print(
                "[red]error: --app conflicts with --category=app; pass one or the other[/red]"
            )
            raise SystemExit(2)
        category = "app"

    if app_category and category != "app":
        console.print(
            "[red]error: --app-category is only valid with --category app (or --app)[/red]"
        )
        raise SystemExit(2)

    try:
        result = _create(
            name,
            description=description,
            template=template,
            category=category,
            app_category=app_category,
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(2)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)

    msg = result.get("message", name)
    final_slug = result.get("slug", "")
    if result.get("is_app"):
        console.print(f"[green]Created app project: {msg}[/green]")
        if final_slug:
            console.print(f"  slug:         [cyan]{final_slug}[/cyan]")
        sub_cat = result.get("app_category") or "<unset>"
        console.print(f"  app_category: [cyan]{sub_cat}[/cyan]")
    else:
        console.print(f"[green]Created project: {msg}[/green]")
        if final_slug:
            console.print(f"  slug: [cyan]{final_slug}[/cyan]")


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
