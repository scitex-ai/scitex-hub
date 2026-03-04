#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/workspace.py
"""
SciTeX Cloud Workspace Commands

Provides workspace operations (upload, list, sync, logout) similar to
how `gh` works for GitHub.

Sub-modules:
    _workspace_auth  -- JWT token cache and authentication helpers
    _workspace_cmds  -- Command implementations (upload, list, sync, logout)

Usage:
    scitex-cloud workspace upload [--name NAME] [--description DESC]
    scitex-cloud workspace list   [--json]
    scitex-cloud workspace sync   [--direction push|pull|both]
    scitex-cloud workspace logout
"""

import click

from ._workspace_cmds import list_projects, logout, sync, upload


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def workspace():
    """Workspace operations (upload, sync, list projects).

    \b
    Manage SciTeX Cloud projects from your local machine, similar to
    how `gh` works for GitHub.

    \b
    Examples:
        scitex-cloud workspace upload --name my-project
        scitex-cloud workspace list
        scitex-cloud workspace sync
        scitex-cloud workspace logout
    """
    pass


workspace.add_command(upload)
workspace.add_command(list_projects, "list")
workspace.add_command(sync)
workspace.add_command(logout)


# EOF
