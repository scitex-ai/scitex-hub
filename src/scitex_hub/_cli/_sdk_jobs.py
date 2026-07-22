#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_cli/_sdk_jobs.py
"""SDK CLI — JobQueue commands (submit, status, close, list).

§1f verb renames: ``show-status`` -> ``status`` and ``cancel`` ->
``close`` (plain rename — the platform cancel endpoint carries no
cancellation reason). The old spellings survive as warn-phase
deprecated aliases until v0.20.
"""

import json

import click

from ._click_compat import (
    register_warn_alias,
    spec_command_kwargs,
    spec_group_kwargs,
)
from ._flags import confirm_or_abort, emit_json, mutating_flags, print_dry_run
from ._sdk_common import _maybe_emit, _read_json


@click.group(
    **spec_group_kwargs(
        summary="JobQueue — background job submission and monitoring.",
        examples=(
            ("{prog} sdk jobs submit my-app export_csv", "Submit a job"),
            ("{prog} sdk jobs status my-app job-123", "Check job status"),
        ),
        command_categories=[("Core", ["submit", "status", "close", "list"])],
    )
)
def jobs():
    """JobQueue — background job submission and monitoring."""
    pass


@jobs.command(
    "submit",
    **spec_command_kwargs(
        summary="Submit a background job.",
        examples=(
            (
                "{prog} sdk jobs submit my-app export_csv "
                "--params '{\"fmt\":\"xlsx\"}'",
                "",
            ),
        ),
    ),
)
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


@jobs.command(
    "status",
    **spec_command_kwargs(
        summary="Get job status and result.",
        examples=(("{prog} sdk jobs status my-app job-123", "Poll one job"),),
    ),
)
@click.argument("app")
@click.argument("job_id")
@_read_json
def jobs_status(app, job_id, as_json):
    """Get job status and result.

    \b
    Example:
        scitex-hub sdk jobs status my-app job-123
    """
    from scitex_hub.sdk import jobs as jobs_api

    result = jobs_api.status(app, job_id)
    _maybe_emit(result, as_json=as_json)


@jobs.command(
    "close",
    **spec_command_kwargs(
        summary="Close (cancel) a running job.",
        examples=(("{prog} sdk jobs close my-app job-123 --yes", "Cancel a job"),),
    ),
)
@click.argument("app")
@click.argument("job_id")
@mutating_flags()
def jobs_cancel(app, job_id, dry_run, yes):
    """Close (cancel) a running job.

    \b
    Example:
        scitex-hub sdk jobs close my-app job-123 --yes
    """
    from scitex_hub.sdk import jobs as jobs_api

    if dry_run:
        print_dry_run(f"would cancel job {job_id!r} on app {app!r}")
        return
    confirm_or_abort(f"Cancel job {job_id!r} on app {app!r}?", yes=yes, dry_run=dry_run)
    result = jobs_api.cancel(app, job_id)
    emit_json(result)


@jobs.command(
    "list",
    **spec_command_kwargs(
        summary="List all jobs for an app.",
        examples=(
            ("{prog} sdk jobs list my-app", "List jobs"),
            ("{prog} sdk jobs list my-app --no-json", "Terse summary"),
        ),
    ),
)
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


# Verb renames (doctrine §1f) — warn-phase aliases until v0.20.
register_warn_alias(
    jobs,
    "show-status",
    target="status",
    remove_in="v0.20",
    target_name="sdk jobs status",
)
register_warn_alias(
    jobs,
    "cancel",
    target="close",
    remove_in="v0.20",
    target_name="sdk jobs close",
)


# EOF
