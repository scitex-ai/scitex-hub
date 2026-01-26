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
    from apps.project_app.services.project_service_manager import ProjectServiceManager

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
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


# EOF
