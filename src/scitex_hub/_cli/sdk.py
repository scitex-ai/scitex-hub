#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDK CLI — interact with Platform APIs (DataStore, FileVault, JobQueue).

Thin orchestrator: the ``sdk`` group plus sub-group registration. The
command implementations live in the sibling modules ``_sdk_data``
(DataStore), ``_sdk_files`` (FileVault) and ``_sdk_jobs`` (JobQueue),
with shared helpers in ``_sdk_common``.

Per §2 universal-flags conventions:
  * Read verbs (``list``, ``get``, ``search``, ``status``) expose
    ``--json`` for machine consumption (default ON — these commands have
    always emitted JSON; the flag now lets callers opt out to a terse
    human summary).
  * Mutating verbs (``create``, ``update``, ``delete``, ``upload``,
    ``download``, ``submit``, ``close``) expose ``--dry-run`` (print the
    plan, do not call the API) and ``-y/--yes`` (skip the interactive
    confirmation on a TTY).

Every leaf carries spec-built help with a concrete example (§4/§4b).
"""

import click

from ._click_compat import spec_group_kwargs
from ._sdk_common import _maybe_emit, _read_json  # noqa: F401 (re-export)
from ._sdk_data import (  # noqa: F401 (re-export)
    data,
    data_create,
    data_delete,
    data_get,
    data_list,
    data_search,
    data_update,
)
from ._sdk_files import (  # noqa: F401 (re-export)
    files,
    files_delete,
    files_download,
    files_list,
    files_upload,
)
from ._sdk_jobs import (  # noqa: F401 (re-export)
    jobs,
    jobs_cancel,
    jobs_list,
    jobs_status,
    jobs_submit,
)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    **spec_group_kwargs(
        summary="Platform SDK — DataStore, FileVault, JobQueue client.",
        examples=(
            ("{prog} sdk data list my-app Experiment", "List records"),
            ("{prog} sdk files upload my-app local.csv exports/data.csv", ""),
            ("{prog} sdk jobs submit my-app export_csv", "Submit a job"),
        ),
        command_categories=[("Core", ["data", "files", "jobs"])],
    ),
)
def sdk():
    """Platform SDK — DataStore, FileVault, JobQueue client.

    \b
    Examples:
        scitex-hub sdk data list my-app Experiment
        scitex-hub sdk files upload my-app local.csv exports/data.csv
        scitex-hub sdk jobs submit my-app export_csv --params '{"fmt":"xlsx"}'
    """
    pass


sdk.add_command(data)
sdk.add_command(files)
sdk.add_command(jobs)


# EOF
