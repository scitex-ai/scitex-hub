#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``scitex-hub app create`` — single-call programmatic app-project creation.

Thin sugar over ``scitex-hub project create --category app`` so the fully
programmatic publish flow has a shorter top-level invocation:

    scitex-hub app create my-tool [--description ...] [--app-category writing]

Mirrors ``scitex-hub project create --app <name>`` exactly: same auto
``_app`` suffix, same is_app=True semantics, same optional sub-category.
Surfaced as a top-level alias because operator 12845 specifically asked
for app-project creation to be a single agent-driven step.
"""

from __future__ import annotations

import click

from .._flags import confirm_or_abort, mutating_flags, print_dry_run
from ._group import app, console


@app.command("create")
@click.argument("name")
@click.option("-d", "--description", default="", help="App project description")
@click.option(
    "-t", "--template", default="scitex_minimal", show_default=True, help="Template ID"
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
        "App sub-category for marketplace listing. Optional at create "
        "time — can also be filled in at `app submit`."
    ),
)
@mutating_flags()
def app_create(name, description, template, app_category, dry_run, yes):
    """Create a new SciTeX Hub app project.

    Equivalent to ``scitex-hub project create <name> --category app``.
    Auto-appends ``_app`` to the name if missing (operator-12845
    convention). Does NOT submit the app to the registry — that's a
    separate ``scitex-hub app submit`` call once the source is ready.

    \b
    Example:
        scitex-hub app create my-tool
        scitex-hub app create my-tool --description "..."
        scitex-hub app create my-tool --app-category writing --yes
        scitex-hub app create my-tool --dry-run
    """
    if dry_run:
        print_dry_run(
            f"create app project name='{name}' template={template} "
            f"app_category={app_category or '<unset>'}"
        )
        return

    confirm_or_abort(
        f"Create app project '{name}' from template '{template}'?",
        yes=yes,
        dry_run=dry_run,
    )

    from scitex_hub.project import project_create as _create

    try:
        result = _create(
            name,
            description=description,
            template=template,
            category="app",
            app_category=app_category,
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(2)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)

    msg = result.get("message", name)
    console.print(f"[green]Created app project: {msg}[/green]")
    final_slug = result.get("slug", "")
    if final_slug:
        console.print(f"  slug:         [cyan]{final_slug}[/cyan]")
    sub_cat = result.get("app_category") or "<unset>"
    console.print(f"  app_category: [cyan]{sub_cat}[/cyan]")


# EOF
