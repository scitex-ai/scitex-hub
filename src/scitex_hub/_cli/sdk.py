#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDK CLI — interact with Platform APIs (DataStore, FileVault, JobQueue)."""

import json
from pathlib import Path

import click


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def sdk():
    """Platform SDK — DataStore, FileVault, JobQueue client.

    \b
    Examples:
        scitex-cloud sdk data list my-app Experiment
        scitex-cloud sdk files upload my-app local.csv exports/data.csv
        scitex-cloud sdk jobs submit my-app export_csv --params '{"fmt":"xlsx"}'
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
def data_list(app, schema, filters, project):
    """List records for an app/schema."""
    from scitex_hub.sdk import data as data_api

    filter_dict = dict(f.split("=", 1) for f in filters) if filters else None
    result = data_api.list_records(app, schema, filters=filter_dict, project_id=project)
    click.echo(json.dumps(result, indent=2))


@data.command("get")
@click.argument("app")
@click.argument("schema")
@click.argument("record_id")
def data_get(app, schema, record_id):
    """Get a single record by ID."""
    from scitex_hub.sdk import data as data_api

    result = data_api.get(app, schema, record_id)
    click.echo(json.dumps(result, indent=2))


@data.command("create")
@click.argument("app")
@click.argument("schema")
@click.option("--json", "json_data", required=True, help="JSON object to create")
def data_create(app, schema, json_data):
    """Create a new record."""
    from scitex_hub.sdk import data as data_api

    payload = json.loads(json_data)
    result = data_api.create(app, schema, payload)
    click.echo(json.dumps(result, indent=2))


@data.command("update")
@click.argument("app")
@click.argument("schema")
@click.argument("record_id")
@click.option("--json", "json_data", required=True, help="JSON object to update")
def data_update(app, schema, record_id, json_data):
    """Update a record by ID."""
    from scitex_hub.sdk import data as data_api

    payload = json.loads(json_data)
    result = data_api.update(app, schema, record_id, payload)
    click.echo(json.dumps(result, indent=2))


@data.command("delete")
@click.argument("app")
@click.argument("schema")
@click.argument("record_id")
def data_delete(app, schema, record_id):
    """Delete a record by ID."""
    from scitex_hub.sdk import data as data_api

    result = data_api.delete(app, schema, record_id)
    click.echo(json.dumps(result, indent=2))


@data.command("search")
@click.argument("app")
@click.argument("schema")
@click.option("--query", "-q", required=True, help="Search query string")
def data_search(app, schema, query):
    """Full-text search across records."""
    from scitex_hub.sdk import data as data_api

    result = data_api.search(app, schema, query)
    click.echo(json.dumps(result, indent=2))


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
def files_list(app, path, project, ext):
    """List files in an app's vault."""
    from scitex_hub.sdk import files as files_api

    result = files_api.list_files(app, path=path, project=project, extensions=ext)
    click.echo(json.dumps(result, indent=2))


@files.command("upload")
@click.argument("app")
@click.argument("local_path", type=click.Path(exists=True))
@click.argument("remote_path")
@click.option("--project", default=None, help="Scope to project")
def files_upload(app, local_path, remote_path, project):
    """Upload a local file to the vault."""
    from scitex_hub.sdk import files as files_api

    content = Path(local_path).read_bytes()
    result = files_api.upload(app, remote_path, content, project=project)
    click.echo(json.dumps(result, indent=2))


@files.command("download")
@click.argument("app")
@click.argument("remote_path")
@click.option("--project", default=None, help="Scope to project")
def files_download(app, remote_path, project):
    """Download a file from the vault."""
    from scitex_hub.sdk import files as files_api

    result = files_api.download(app, remote_path, project=project)
    click.echo(json.dumps(result, indent=2))


@files.command("delete")
@click.argument("app")
@click.argument("remote_path")
@click.option("--project", default=None, help="Scope to project")
def files_delete(app, remote_path, project):
    """Delete a file from the vault."""
    from scitex_hub.sdk import files as files_api

    result = files_api.delete(app, remote_path, project=project)
    click.echo(json.dumps(result, indent=2))


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
def jobs_submit(app, job_name, params_json, project):
    """Submit a background job."""
    from scitex_hub.sdk import jobs as jobs_api

    params = json.loads(params_json) if params_json else None
    result = jobs_api.submit(app, job_name, params=params, project_id=project)
    click.echo(json.dumps(result, indent=2))


@jobs.command("show-status")
@click.argument("app")
@click.argument("job_id")
def jobs_status(app, job_id):
    """Get job status and result."""
    from scitex_hub.sdk import jobs as jobs_api

    result = jobs_api.status(app, job_id)
    click.echo(json.dumps(result, indent=2))


@jobs.command("cancel")
@click.argument("app")
@click.argument("job_id")
def jobs_cancel(app, job_id):
    """Cancel a running job."""
    from scitex_hub.sdk import jobs as jobs_api

    result = jobs_api.cancel(app, job_id)
    click.echo(json.dumps(result, indent=2))


@jobs.command("list")
@click.argument("app")
def jobs_list(app):
    """List all jobs for an app."""
    from scitex_hub.sdk import jobs as jobs_api

    result = jobs_api.list_jobs(app)
    click.echo(json.dumps(result, indent=2))


# EOF
