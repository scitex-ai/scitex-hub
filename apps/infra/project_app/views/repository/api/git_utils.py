#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git utility functions for git operations.

Provides:
- Project path retrieval
- Git command execution wrapper
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def get_project_path(project):
    """Get the filesystem path for a project."""
    from apps.infra.project_app.services.project_service_manager import (
        ProjectServiceManager,
    )

    service_manager = ProjectServiceManager(project)
    return service_manager.get_project_path()


def run_git_command(
    project_path: Path, args: List[str], timeout: int = 30
) -> tuple[bool, str, str]:
    """
    Run a git command and return (success, stdout, stderr).

    Args:
        project_path: Path to the git repository
        args: Git command arguments (without 'git' prefix)
        timeout: Command timeout in seconds

    Returns:
        Tuple of (success, stdout, stderr)

    Network operations reached through this wrapper (``push`` / ``pull`` /
    ``fetch``) must authenticate to Gitea, and the credential is supplied
    per-invocation through the ENVIRONMENT rather than through the origin URL
    -- ``.git/config`` is bind-mounted read/write into the user's console, so
    a token written there leaks the platform admin credential across tenants
    (sec-gitea-admin-token-plaintext-in-user-gitconfig).

    ``build_gitea_auth_env()`` is applied to EVERY invocation, not only the
    network ones: the header it installs is scoped to the Gitea origin
    (``http.<gitea-url>.extraHeader``), so it is inert for a local-only
    command, and deciding per-verb is the kind of branch that goes stale the
    next time a verb is added. It also sets ``GIT_TERMINAL_PROMPT=0``, so a
    missing credential fails loud instead of hanging on a prompt no server
    process can answer.
    """
    from apps.infra.project_app.services.git_service import build_gitea_auth_env

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_gitea_auth_env(),
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


# EOF
