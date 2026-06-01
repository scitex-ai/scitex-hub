#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``app check-deps`` / ``app install-deps`` / ``app build-container`` verbs."""

from __future__ import annotations

import json as _json
from pathlib import Path

import click

from .._flags import confirm_or_abort, mutating_flags, print_dry_run
from ._group import app, console


@app.command("check-deps")
@click.argument("app_dir", default=".", type=click.Path(exists=True))
def app_check_deps(app_dir) -> None:
    """Check app dependencies from manifest.json.

    \b
    Example:
        scitex-hub app check-deps .
        scitex-hub app check-deps /path/to/my_app
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
@mutating_flags()
def app_install_deps(app_dir, dep_type, dry_run, yes) -> None:
    """Install app dependencies of a specific type.

    \b
    Example:
        scitex-hub app install-deps . --type python
        scitex-hub app install-deps . -t system --yes
    """
    from scitex_hub.appmaker import install_deps

    manifest_path = Path(app_dir) / "manifest.json"
    if not manifest_path.is_file():
        console.print("[red]No manifest.json found[/red]")
        raise SystemExit(1)

    if dry_run:
        print_dry_run(
            f"would install {dep_type} dependencies declared in {manifest_path}"
        )
        return

    confirm_or_abort(
        f"Install {dep_type} dependencies from {manifest_path}?",
        yes=yes,
        dry_run=dry_run,
    )

    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
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
@mutating_flags()
def app_build_container(app_dir, output_dir, dry_run, yes) -> None:
    """Build an Apptainer container from an app's .def file.

    Reads the ``container`` field from manifest.json and builds a .sif image.

    \b
    Example:
        scitex-hub app build-container .
        scitex-hub app build-container /path/to/my_app -o /data/containers/
    """
    from scitex_hub.appmaker import build_container

    out = Path(output_dir) if output_dir else None
    target = Path(app_dir).resolve()

    if dry_run:
        print_dry_run(
            f"would build Apptainer container from {target} (output={out or 'default'})"
        )
        return

    confirm_or_abort(
        f"Build Apptainer container from {target}?", yes=yes, dry_run=dry_run
    )

    console.print(f"[cyan]Building container from:[/cyan] {target}")

    result = build_container(target, output_dir=out)

    if result["success"]:
        console.print(f"[green]Built:[/green] {result['sif_path']}")
    else:
        console.print(f"[red]Failed:[/red] {result['error']}")
        raise SystemExit(1)


# EOF
