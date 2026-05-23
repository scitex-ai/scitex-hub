#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_utils/_project_nav.py

"""Project directory navigation — shared by cloud terminal and standalone mode.

Provides shell-safe cd commands with user-friendly messages for project
switching. Used by terminal broker, standalone launcher, and CLI tools.
"""

from __future__ import annotations


def build_cd_command(username: str, project_slug: str) -> str:
    """Build a shell command to cd into a project directory.

    Returns a shell snippet that:
    - Changes to /home/{username}/proj/{project_slug} if it exists
    - Prints a warning if the directory is missing

    Parameters
    ----------
    username : str
        Container username (determines home dir).
    project_slug : str
        Project slug (directory name under ~/proj/).

    Returns
    -------
    str
        Shell command string safe to write to a PTY.
    """
    project_dir = f"/home/{username}/proj/{project_slug}"
    return (
        f'if [ -d "{project_dir}" ]; then '
        f'cd "{project_dir}"; '
        f"else "
        f'echo "⚠ Project directory {project_dir} not found '
        f'— project may have changed on SciTeX Cloud"; '
        f"fi"
    )


def build_switch_command(username: str, project_slug: str) -> str:
    """Build a shell command for switching to a different project.

    Like build_cd_command but also prints a confirmation message on success.

    Parameters
    ----------
    username : str
        Container username.
    project_slug : str
        Target project slug.

    Returns
    -------
    str
        Shell command string safe to write to a PTY.
    """
    project_dir = f"/home/{username}/proj/{project_slug}"
    return (
        f'if [ -d "{project_dir}" ]; then '
        f'cd "{project_dir}" && '
        f'echo "📂 Project switched to: {project_slug}"; '
        f"else "
        f'echo "⚠ Project directory {project_dir} not found"; '
        f"fi"
    )


# EOF
