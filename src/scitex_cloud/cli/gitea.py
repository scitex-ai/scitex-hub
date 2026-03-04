#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/gitea.py
"""
SciTeX Cloud Gitea Commands - Wrapper for tea (Gitea CLI)

Provides git/repository operations by wrapping the tea command.
Usage: scitex-cloud gitea {login,logout,clone,create,list,search,delete,fork,pr,issue,push,pull,status,enrich}
"""

import click

from ._gitea_auth import login, logout
from ._gitea_collab import enrich, issue, pr, pull, push, status
from ._gitea_repo import clone, create, delete, fork, list_repos, search


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
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


# EOF
