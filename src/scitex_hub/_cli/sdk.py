#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDK CLI — interact with Platform APIs (DataStore, FileVault, JobQueue).

Per §2 universal-flags conventions:
  * Read verbs (``list``, ``get``, ``search``, ``show-status``) expose
    ``--json`` for machine consumption (default ON — these commands have
    always emitted JSON; the flag now lets callers opt out to a terse
    human summary).
  * Mutating verbs (``create``, ``update``, ``delete``, ``upload``,
    ``download``, ``submit``, ``cancel``) expose ``--dry-run`` (print the
    plan, do not call the API) and ``-y/--yes`` (skip the interactive
    confirmation on a TTY).

Every command carries a concrete ``Example:`` block in its docstring per §4.
"""

import json
from pathlib import Path

import click

from ._flags import (
    confirm_or_abort,
    emit_json,
    mutating_flags,
    print_dry_run,
)


def _maybe_emit(result, *, as_json: bool) -> None:
    """Render *result* either as pretty JSON or a one-line human summary.

    Default behaviour preserves the historical JSON output. The ``--no-json``
    branch prints a short summary so shell pipelines can opt into terse
    output without parsing JSON.
    """

    if as_json:
        emit_json(result)
        return
    if isinstance(result, list):
        click.echo(f"{len(result)} item(s)")
        return
    if isinstance(result, dict):
        keys = ", ".join(sorted(result)[:8])
        click.echo(f"dict[{len(result)} keys]: {keys}")
        return
    click.echo(str(result))


# Shared decorator for read verbs: --json defaults to True (historical).
_read_json = click.option(
    "--json/--no-json",
    "as_json",
    default=True,
    help="Output as JSON (default). Use --no-json for a short summary.",
)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def sdk():
    """Platform SDK — DataStore, FileVault, JobQueue client.

    \b
    Examples:
        scitex-hub sdk data list my-app Experiment
        scitex-hub sdk files upload my-app local.csv exports/data.csv
        scitex-hub sdk jobs submit my-app export_csv --params '{"fmt":"xlsx"}'
    """
    pass


# ── DataStore ──────────────────────────────────────────────────────────


@sdk.group()
def data():
    """DataStore — CRUD + search for app-scoped JSON data."""
    pass


@data.command("list")
@click.argument("app")
@click.argument("schema")
@click.option("--filter", "filters", multiple=True, help="key=value filter pairs")
@click.option("--project", default=None, help="Scope to project ID")
@_read_json
def data_list(app, schema, filters, project, as_json):
    """List records for an app/schema.

    \b
    Example:
        scitex-hub sdk data list my-app Experiment
        scitex-hub sdk data list my-app Experiment --filter status=done --json
    """
    from scitex_hub.sdk import data as data_api

    filter_dict = dict(f.split("=", 1) for f in filters) if filters else None
    result = data_api.list_records(app, schema, filters=filter_dict, project_id=project)
    _maybe_emit(result, as_json=as_json)


@data.command("get")
@click.argument("app")
@click.argument("schema")
@click.argument("record_id")
@_read_json
def data_get(app, schema, record_id, as_json):
    """Get a single record by ID.

    \b
    Example:
        scitex-hub sdk data get my-app Experiment 42
    """
    from scitex_hub.sdk import data as data_api

    result = data_api.get(app, schema, record_id)
    _maybe_emit(result, as_json=as_json)


@data.command("create")
@click.argument("app")
@click.argument("schema")
@click.option("--json", "json_data", required=True, help="JSON object to create")
@mutating_flags()
def data_create(app, schema, json_data, dry_run, yes):
    """Create a new record.

    \b
    Example:
        scitex-hub sdk data create my-app Experiment --json '{"name":"x"}'
        scitex-hub sdk data create my-app Experiment --json '{...}' --yes
    """
    from scitex_hub.sdk import data as data_api

    payload = json.loads(json_data)
    if dry_run:
        print_dry_run(f"would create {schema!r} record in app {app!r}: {payload}")
        return
    confirm_or_abort(
        f"Create {schema!r} record in app {app!r}?", yes=yes, dry_run=dry_run
    )
    result = data_api.create(app, schema, payload)
    emit_json(result)


@data.command("update")
@click.argument("app")
@click.argument("schema")
@click.argument("record_id")
@click.option("--json", "json_data", required=True, help="JSON object to update")
@mutating_flags()
def data_update(app, schema, record_id, json_data, dry_run, yes):
    """Update a record by ID.

    \b
    Example:
        scitex-hub sdk data update my-app Experiment 42 --json '{"status":"done"}'
    """
    from scitex_hub.sdk import data as data_api

    payload = json.loads(json_data)
    if dry_run:
        print_dry_run(
            f"would update {schema!r} record {record_id!r} in app {app!r}: {payload}"
        )
        return
    confirm_or_abort(
        f"Update {schema!r} record {record_id!r} in app {app!r}?",
        yes=yes,
        dry_run=dry_run,
    )
    result = data_api.update(app, schema, record_id, payload)
    emit_json(result)


@data.command("delete")
@click.argument("app")
@click.argument("schema")
@click.argument("record_id")
@mutating_flags()
def data_delete(app, schema, record_id, dry_run, yes):
    """Delete a record by ID.

    \b
    Example:
        scitex-hub sdk data delete my-app Experiment 42 --yes
    """
    from scitex_hub.sdk import data as data_api

    if dry_run:
        print_dry_run(f"would delete {schema!r} record {record_id!r} in app {app!r}")
        return
    confirm_or_abort(
        f"Delete {schema!r} record {record_id!r} in app {app!r}?",
        yes=yes,
        dry_run=dry_run,
    )
    result = data_api.delete(app, schema, record_id)
    emit_json(result)


@data.command("search")
@click.argument("app")
@click.argument("schema")
@click.option("--query", "-q", required=True, help="Search query string")
@_read_json
def data_search(app, schema, query, as_json):
    """Full-text search across records.

    \b
    Example:
        scitex-hub sdk data search my-app Experiment -q "kw=ripple"
    """
    from scitex_hub.sdk import data as data_api

    result = data_api.search(app, schema, query)
    _maybe_emit(result, as_json=as_json)


# ── FileVault ──────────────────────────────────────────────────────────


@sdk.group()
def files():
    """FileVault — per-app namespaced file storage."""
    pass


@files.command("list")
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


@files.command("upload")
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


@files.command("download")
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


@files.command("delete")
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


# ── JobQueue ───────────────────────────────────────────────────────────


@sdk.group()
def jobs():
    """JobQueue — background job submission and monitoring."""
    pass


@jobs.command("submit")
@click.argument("app")
@click.argument("job_name")
@click.option("--params", "params_json", default=None, help="JSON params for the job")
@click.option("--project", default=None, help="Scope to project ID")
@mutating_flags()
def jobs_submit(app, job_name, params_json, project, dry_run, yes):
    """Submit a background job.

    \b
    Example:
        scitex-hub sdk jobs submit my-app export_csv --params '{"fmt":"xlsx"}'
    """
    from scitex_hub.sdk import jobs as jobs_api

    params = json.loads(params_json) if params_json else None
    if dry_run:
        print_dry_run(
            f"would submit job {job_name!r} on app {app!r} with params {params!r}"
        )
        return
    confirm_or_abort(
        f"Submit job {job_name!r} on app {app!r}?", yes=yes, dry_run=dry_run
    )
    result = jobs_api.submit(app, job_name, params=params, project_id=project)
    emit_json(result)


@jobs.command("show-status")
@click.argument("app")
@click.argument("job_id")
@_read_json
def jobs_status(app, job_id, as_json):
    """Get job status and result.

    \b
    Example:
        scitex-hub sdk jobs show-status my-app job-123
    """
    from scitex_hub.sdk import jobs as jobs_api

    result = jobs_api.status(app, job_id)
    _maybe_emit(result, as_json=as_json)


@jobs.command("cancel")
@click.argument("app")
@click.argument("job_id")
@mutating_flags()
def jobs_cancel(app, job_id, dry_run, yes):
    """Cancel a running job.

    \b
    Example:
        scitex-hub sdk jobs cancel my-app job-123 --yes
    """
    from scitex_hub.sdk import jobs as jobs_api

    if dry_run:
        print_dry_run(f"would cancel job {job_id!r} on app {app!r}")
        return
    confirm_or_abort(f"Cancel job {job_id!r} on app {app!r}?", yes=yes, dry_run=dry_run)
    result = jobs_api.cancel(app, job_id)
    emit_json(result)


@jobs.command("list")
@click.argument("app")
@_read_json
def jobs_list(app, as_json):
    """List all jobs for an app.

    \b
    Example:
        scitex-hub sdk jobs list my-app
        scitex-hub sdk jobs list my-app --no-json
    """
    from scitex_hub.sdk import jobs as jobs_api

    result = jobs_api.list_jobs(app)
    _maybe_emit(result, as_json=as_json)


# EOF
