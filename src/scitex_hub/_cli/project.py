#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/project.py
"""Project CRUD CLI commands."""

import click
from rich.console import Console
from rich.table import Table

from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._flags import (
    confirm_or_abort,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
)

console = Console()


@click.group(**spec_group_kwargs(summary="Manage SciTeX Hub projects."))
def project():
    """Manage SciTeX Hub projects.

    \b
    Example:
        scitex-hub project list
        scitex-hub project list --json
        scitex-hub project create my-research --description "Paper on X"
        scitex-hub project create my-research --dry-run
        scitex-hub project delete my-research --yes
        scitex-hub project rename my-research new-name --yes
    """


@project.command(
    "list",
    **spec_command_kwargs(
        summary="List all your projects.",
        examples=(("{prog} project list", "List your projects."),),
    ),
)
@json_flag()
def project_list(json_output):
    """List all your projects.

    \b
    Example:
        scitex-hub project list
        scitex-hub project list --json
    """
    from scitex_hub.project import project_list as _list

    try:
        projects = _list()
    except RuntimeError as e:
        if json_output:
            emit_json({"success": False, "error": str(e)})
            raise SystemExit(1)
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)

    if json_output:
        emit_json({"success": True, "projects": projects})
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


@project.command(
    "create",
    **spec_command_kwargs(
        summary="Create a new project.",
        examples=(("{prog} project create my-research --yes", "Create a project."),),
    ),
)
@click.argument("name")
@click.option("-d", "--description", default="", help="Project description")
@click.option("-t", "--template", default="scitex_minimal", help="Template ID")
@mutating_flags()
def project_create(name, description, template, dry_run, yes):
    """Create a new project.

    \b
    Example:
        scitex-hub project create my-research
        scitex-hub project create my-research --description "Paper on X"
        scitex-hub project create my-research --template scitex_minimal
        scitex-hub project create my-research --dry-run
        scitex-hub project create my-research --yes
    """
    if dry_run:
        print_dry_run(
            f"create project '{name}' (template={template}, description={description!r})"
        )
        return

    confirm_or_abort(f"Create project '{name}'?", yes=yes, dry_run=dry_run)

    from scitex_hub.project import project_create as _create

    try:
        result = _create(name, description=description, template=template)
        console.print(f"[green]Created project: {result.get('message', name)}[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@project.command(
    "delete",
    **spec_command_kwargs(
        summary="Delete a project by slug.",
        examples=(("{prog} project delete my-research --yes", "Delete a project."),),
    ),
)
@click.argument("slug")
@mutating_flags()
def project_delete(slug, dry_run, yes):
    """Delete a project by slug.

    Destructive — requires --yes/-y (never prompts).

    \b
    Example:
        scitex-hub project delete my-research --yes
        scitex-hub project delete my-research --dry-run
    """
    if dry_run:
        print_dry_run(f"delete project '{slug}'")
        return

    confirm_or_abort(
        f"Delete project '{slug}'? This is irreversible.",
        yes=yes,
        dry_run=dry_run,
    )

    from scitex_hub.project import project_delete as _delete

    try:
        _delete(slug)
        console.print(f"[green]Deleted project: {slug}[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@project.command(
    "rename",
    **spec_command_kwargs(
        summary="Rename a project.",
        examples=(
            ("{prog} project rename my-research new-name --yes", "Rename a project."),
        ),
    ),
)
@click.argument("slug")
@click.argument("new_name")
@mutating_flags()
def project_rename(slug, new_name, dry_run, yes):
    """Rename a project.

    \b
    Example:
        scitex-hub project rename my-research new-research-name
        scitex-hub project rename my-research new-name --yes
        scitex-hub project rename my-research new-name --dry-run
    """
    if dry_run:
        print_dry_run(f"rename project '{slug}' -> '{new_name}'")
        return

    confirm_or_abort(
        f"Rename project '{slug}' to '{new_name}'?",
        yes=yes,
        dry_run=dry_run,
    )

    from scitex_hub.project import project_rename as _rename

    try:
        _rename(slug, new_name)
        console.print(f"[green]Renamed '{slug}' to '{new_name}'[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# EOF
