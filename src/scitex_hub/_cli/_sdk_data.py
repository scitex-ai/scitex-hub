#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/_sdk_data.py
"""SDK CLI — DataStore commands (list, get, create, update, delete, search)."""

import json

import click

from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._flags import confirm_or_abort, emit_json, mutating_flags, print_dry_run
from ._sdk_common import _maybe_emit, _read_json


@click.group(
    **spec_group_kwargs(
        summary="DataStore — CRUD + search for app-scoped JSON data.",
        examples=(
            ("{prog} sdk data list my-app Experiment", "List records"),
            ("{prog} sdk data get my-app Experiment 42", "Get one record"),
        ),
        command_categories=[
            ("Core", ["list", "get", "create", "update", "delete", "search"]),
        ],
    )
)
def data():
    """DataStore — CRUD + search for app-scoped JSON data."""
    pass


@data.command(
    "list",
    **spec_command_kwargs(
        summary="List records for an app/schema.",
        examples=(
            ("{prog} sdk data list my-app Experiment", "All records"),
            ("{prog} sdk data list my-app Experiment --filter status=done", ""),
        ),
    ),
)
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


@data.command(
    "get",
    **spec_command_kwargs(
        summary="Get a single record by ID.",
        examples=(("{prog} sdk data get my-app Experiment 42", "Fetch record 42"),),
    ),
)
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


@data.command(
    "create",
    **spec_command_kwargs(
        summary="Create a new record.",
        examples=(
            ("{prog} sdk data create my-app Experiment --json '{\"name\":\"x\"}'", ""),
            ("{prog} sdk data create my-app Experiment --json '{}' --yes", ""),
        ),
    ),
)
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


@data.command(
    "update",
    **spec_command_kwargs(
        summary="Update a record by ID.",
        examples=(
            (
                "{prog} sdk data update my-app Experiment 42 "
                "--json '{\"status\":\"done\"}'",
                "",
            ),
        ),
    ),
)
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


@data.command(
    "delete",
    **spec_command_kwargs(
        summary="Delete a record by ID.",
        examples=(("{prog} sdk data delete my-app Experiment 42 --yes", ""),),
    ),
)
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


@data.command(
    "search",
    **spec_command_kwargs(
        summary="Full-text search across records.",
        examples=(("{prog} sdk data search my-app Experiment -q 'kw=ripple'", ""),),
    ),
)
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


# EOF
