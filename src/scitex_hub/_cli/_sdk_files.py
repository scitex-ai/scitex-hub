#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/_sdk_files.py
"""SDK CLI — FileVault commands (list, upload, download, delete)."""

from pathlib import Path

import click

from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._flags import confirm_or_abort, emit_json, mutating_flags, print_dry_run
from ._sdk_common import _maybe_emit, _read_json


@click.group(
    **spec_group_kwargs(
        summary="FileVault — per-app namespaced file storage.",
        examples=(
            ("{prog} sdk files list my-app --path exports", "List vault files"),
            ("{prog} sdk files upload my-app local.csv exports/data.csv", ""),
        ),
        command_categories=[("Core", ["list", "upload", "download", "delete"])],
    )
)
def files():
    """FileVault — per-app namespaced file storage."""
    pass


@files.command(
    "list",
    **spec_command_kwargs(
        summary="List files in an app's vault.",
        examples=(
            ("{prog} sdk files list my-app --path exports", "List a subdir"),
            ("{prog} sdk files list my-app --ext csv --json", "Filter + JSON"),
        ),
    ),
)
@click.argument("app")
@click.option("--path", default="", help="Subdirectory path")
@click.option("--project", default=None, help="Scope to project")
@click.option("--ext", default=None, help="Filter by file extension")
@_read_json
def files_list(app, path, project, ext, as_json):
    """List files in an app's vault.

    \b
    Example:
        scitex-hub sdk files list my-app --path exports
        scitex-hub sdk files list my-app --ext csv --json
    """
    from scitex_hub.sdk import files as files_api

    result = files_api.list_files(app, path=path, project=project, extensions=ext)
    _maybe_emit(result, as_json=as_json)


@files.command(
    "upload",
    **spec_command_kwargs(
        summary="Upload a local file to the vault.",
        examples=(
            ("{prog} sdk files upload my-app local.csv exports/data.csv", ""),
            ("{prog} sdk files upload my-app local.csv exports/data.csv --yes", ""),
        ),
    ),
)
@click.argument("app")
@click.argument("local_path", type=click.Path(exists=True))
@click.argument("remote_path")
@click.option("--project", default=None, help="Scope to project")
@mutating_flags()
def files_upload(app, local_path, remote_path, project, dry_run, yes):
    """Upload a local file to the vault.

    \b
    Example:
        scitex-hub sdk files upload my-app local.csv exports/data.csv
        scitex-hub sdk files upload my-app local.csv exports/data.csv --yes
    """
    from scitex_hub.sdk import files as files_api

    if dry_run:
        size = Path(local_path).stat().st_size
        print_dry_run(
            f"would upload {local_path!r} ({size} B) to app {app!r} as {remote_path!r}"
        )
        return
    confirm_or_abort(
        f"Upload {local_path!r} to app {app!r} as {remote_path!r}?",
        yes=yes,
        dry_run=dry_run,
    )
    content = Path(local_path).read_bytes()
    result = files_api.upload(app, remote_path, content, project=project)
    emit_json(result)


@files.command(
    "download",
    **spec_command_kwargs(
        summary="Download a file from the vault.",
        examples=(("{prog} sdk files download my-app exports/data.csv", ""),),
    ),
)
@click.argument("app")
@click.argument("remote_path")
@click.option("--project", default=None, help="Scope to project")
@mutating_flags()
def files_download(app, remote_path, project, dry_run, yes):
    """Download a file from the vault.

    \b
    Example:
        scitex-hub sdk files download my-app exports/data.csv
    """
    from scitex_hub.sdk import files as files_api

    if dry_run:
        print_dry_run(f"would download {remote_path!r} from app {app!r}")
        return
    confirm_or_abort(
        f"Download {remote_path!r} from app {app!r}?", yes=yes, dry_run=dry_run
    )
    result = files_api.download(app, remote_path, project=project)
    emit_json(result)


@files.command(
    "delete",
    **spec_command_kwargs(
        summary="Delete a file from the vault.",
        examples=(("{prog} sdk files delete my-app exports/data.csv --yes", ""),),
    ),
)
@click.argument("app")
@click.argument("remote_path")
@click.option("--project", default=None, help="Scope to project")
@mutating_flags()
def files_delete(app, remote_path, project, dry_run, yes):
    """Delete a file from the vault.

    \b
    Example:
        scitex-hub sdk files delete my-app exports/data.csv --yes
    """
    from scitex_hub.sdk import files as files_api

    if dry_run:
        print_dry_run(f"would delete {remote_path!r} from app {app!r}")
        return
    confirm_or_abort(
        f"Delete {remote_path!r} from app {app!r}?", yes=yes, dry_run=dry_run
    )
    result = files_api.delete(app, remote_path, project=project)
    emit_json(result)


# EOF
