#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/workspace.py
"""
SciTeX Hub Workspace Commands

Provides workspace operations (upload, list, push, pull, status, sync,
logout) similar to how `gh` works for GitHub.

Sub-modules:
    _workspace_auth  -- JWT token cache and authentication helpers
    _workspace_cmds  -- Command implementations (upload, list, sync, logout)
    sync             -- Dropbox-style push / pull / status leaves

Usage:
    scitex-hub workspace upload [--name NAME] [--description DESC]
    scitex-hub workspace list   [--json]
    scitex-hub workspace push   [REPO]   # working files -> workspace
    scitex-hub workspace pull   [REPO]   # working files <- workspace
    scitex-hub workspace status [REPO]   # 3-way divergence
    scitex-hub workspace sync   [--direction push|pull|both]
    scitex-hub workspace logout
"""

import click

from ._click_compat import spec_group_kwargs
from ._workspace_cmds import list_projects, logout, sync, upload
from .sync import sync_from, sync_status, sync_to

_WORKSPACE_CATEGORIES = [
    ("Core", ["upload", "list", "logout"]),
    ("Data & Sync", ["push", "pull", "sync"]),
    ("Diagnostics", ["status"]),
]


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    **spec_group_kwargs(
        summary="Workspace operations (upload, push/pull, sync, list).",
        description=(
            "Manage SciTeX Hub projects from your local machine, "
            "similar to how `gh` works for GitHub. `push`/`pull` move "
            "working files Dropbox-style; `sync` reconciles committed "
            "changes via git.",
        ),
        examples=(
            ("{prog} workspace upload --name my-project", "Create + push"),
            ("{prog} workspace list", "List your projects"),
            ("{prog} workspace push", "Working files -> workspace"),
            ("{prog} workspace pull", "Working files <- workspace"),
            ("{prog} workspace status", "3-way sync state"),
            ("{prog} workspace logout", "Clear the cached token"),
        ),
        command_categories=_WORKSPACE_CATEGORIES,
    ),
)
def workspace():
    """Workspace operations (upload, push/pull, sync, list projects).

    \b
    Manage SciTeX Hub projects from your local machine, similar to
    how `gh` works for GitHub.

    \b
    Examples:
        scitex-hub workspace upload --name my-project
        scitex-hub workspace list
        scitex-hub workspace push
        scitex-hub workspace pull
        scitex-hub workspace status
        scitex-hub workspace sync
        scitex-hub workspace logout
    """
    pass


workspace.add_command(upload)
workspace.add_command(list_projects, "list")
workspace.add_command(sync)
workspace.add_command(logout)
# Slice 6a verb renames (doctrine §1d): the Dropbox-style sync family
# is directional transfer, so it lives here as push / pull / status.
# The old root spellings (sync-to / sync-from / sync-status / ss) are
# warn-phase deprecated aliases registered in sync.py.
workspace.add_command(sync_to)  # workspace push
workspace.add_command(sync_from)  # workspace pull
workspace.add_command(sync_status)  # workspace status


# EOF
