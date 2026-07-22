#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/gitea.py
"""
SciTeX Hub Gitea Commands - Wrapper for tea (Gitea CLI)

Provides git/repository operations by wrapping the tea command.
Usage: scitex-hub gitea {login,logout,clone,create,list,search,delete,fork,pr,issue,push,pull,status,enrich}
"""

import click

from ._click_compat import register_warn_alias, spec_group_kwargs
from ._gitea_auth import login, logout
from ._gitea_collab import enrich, issue, pr, pull, push, status
from ._gitea_repo import clone, create, delete, fork, list_repos, search

_GITEA_CATEGORIES = [
    ("Core", ["login", "logout", "clone", "create", "list", "search",
              "delete", "fork", "pr", "issue"]),
    ("Data & Sync", ["push", "pull", "enrich"]),
    ("Diagnostics", ["status"]),
]


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    **spec_group_kwargs(
        summary="Gitea operations (wraps the tea CLI).",
        description=(
            "Standard git hosting operations against the SciTeX Hub "
            "Gitea backend (git.scitex.ai): repository management "
            "(create, list, delete), cloning and forking, pull "
            "requests and issues.",
        ),
        examples=(
            ("{prog} gitea login --token $SCITEX_HUB_GITEA_TOKEN", "Authenticate"),
            ("{prog} gitea clone scitex-dev/scitex-hub", "Clone a repo"),
            ("{prog} gitea pr list --json", "List PRs as JSON"),
            ("{prog} gitea status", "Show repository status"),
        ),
        command_categories=_GITEA_CATEGORIES,
    ),
)
def gitea():
    """
    Gitea operations (wraps tea CLI)

    \b
    Provides standard git hosting operations:
    - Repository management (create, list, delete)
    - Cloning and forking
    - Pull requests and issues

    \b
    Backend: Gitea (git.scitex.ai)
    """
    pass


# Authentication
gitea.add_command(login)
gitea.add_command(logout)

# Repository management
gitea.add_command(clone)
gitea.add_command(create)
gitea.add_command(list_repos)
gitea.add_command(search)
gitea.add_command(delete)
gitea.add_command(fork)

# Collaboration
gitea.add_command(pr)
gitea.add_command(issue)
gitea.add_command(push)
gitea.add_command(pull)
gitea.add_command(status)
gitea.add_command(enrich)

# Verb renames (doctrine §1f): `show-status` -> `status`; the old
# spelling survives as a warn-phase deprecated alias until v0.20.
register_warn_alias(
    gitea,
    "show-status",
    target="status",
    remove_in="v0.20",
    target_name="gitea status",
)


# EOF
