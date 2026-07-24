#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 20:15:00 (ywatanabe)"
# File: ./apps/workspace_app/git_operations.py

"""
Git operations for SciTeX Hub

Provides helper functions for git operations on Django projects
that are backed by Gitea repositories.
"""

import base64
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


def strip_url_credentials(url: str) -> str:
    """Return ``url`` with any ``user[:password]@`` userinfo removed.

    ``http://alice:TOKEN@gitea:3000/a/b.git`` -> ``http://gitea:3000/a/b.git``
    and ``http://TOKEN@gitea:3000/a/b.git`` -> ``http://gitea:3000/a/b.git``.
    Non-``scheme://`` URLs (e.g. ``git@host:path`` SSH) are returned untouched.

    Only the AUTHORITY component is examined — an ``@`` later in the path is
    left alone, so ``http://gitea:3000/u/re@po.git`` survives intact instead
    of being mangled into ``http://po.git``.
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    authority, slash, path = rest.partition("/")
    if "@" in authority:
        # Last '@' wins: userinfo may legally contain an escaped '@', and this
        # matches how git/curl split the authority.
        authority = authority.rsplit("@", 1)[1]
    return f"{scheme}://{authority}{slash}{path}"


def build_gitea_auth_env(
    token: Optional[str] = None,
    gitea_url: Optional[str] = None,
    base_env: Optional[dict] = None,
) -> dict:
    """Environment for a git invocation that must authenticate to Gitea.

    SECURITY (sec-gitea-admin-token-plaintext-in-user-gitconfig): the platform
    Gitea token must NEVER be written into a repo's ``.git/config`` (origin
    URL) — that file is bind-mounted read/write into the user's Apptainer
    console at ``/workspace``, so a token there leaks the platform ADMIN
    credential across tenants.

    The token is therefore supplied per-invocation, and via the ENVIRONMENT
    (``GIT_CONFIG_COUNT`` / ``GIT_CONFIG_KEY_0`` / ``GIT_CONFIG_VALUE_0``,
    git >= 2.31) rather than ``git -c ...`` on the command line: argv is
    world-readable through ``/proc/<pid>/cmdline``, so the ``-c`` form would
    merely move the leak from ``.git/config`` to the process table instead of
    closing it. A process's environ is readable only by the same uid (or
    root), which is the boundary we need.

    The header is SCOPED to the Gitea origin (``http.<gitea-url>.extraHeader``)
    so the admin credential is never attached to a request to another host
    (e.g. after an HTTP redirect).

    Always sets ``GIT_TERMINAL_PROMPT=0`` so a missing credential fails loud
    instead of hanging on an interactive prompt.
    """
    env = dict(os.environ if base_env is None else base_env)
    env["GIT_TERMINAL_PROMPT"] = "0"

    token = token if token is not None else getattr(settings, "GITEA_TOKEN", "")
    url = gitea_url if gitea_url is not None else getattr(settings, "GITEA_URL", "")
    url = (url or "").rstrip("/")
    if not token or not url:
        # Nothing to inject — git runs unauthenticated and fails loud.
        return env

    # Gitea git-over-HTTP accepts the token as the Basic-auth username with an
    # empty password (the same bytes the previously-working
    # ``http://<token>@host`` clone URL sent).
    basic = base64.b64encode(f"{token}:".encode()).decode()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = f"http.{url}.extraHeader"
    env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
    return env


def git_commit_and_push(
    project_dir: Path,
    message: str,
    files: Optional[List[str]] = None,
    branch: str = "develop",
    push: bool = True,
) -> Tuple[bool, str]:
    """
    Commit changes and optionally push to Gitea.

    Args:
        project_dir: Path to project directory (must be a git repo)
        message: Commit message
        files: List of files to commit (None = all changes)
        branch: Branch name (default: develop)
        push: Whether to push to remote (default: True)

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        project_dir = Path(project_dir)

        if not (project_dir / ".git").exists():
            return False, f"Not a git repository: {project_dir}"

        # Add files
        if files:
            for file in files:
                result = subprocess.run(
                    ["git", "add", file],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return False, f"git add failed: {result.stderr}"
        else:
            # Add all changes
            result = subprocess.run(
                ["git", "add", "."], cwd=project_dir, capture_output=True, text=True
            )
            if result.returncode != 0:
                return False, f"git add failed: {result.stderr}"

        # Check if there are changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if not status.stdout.strip():
            return True, "No changes to commit"

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return False, f"git commit failed: {result.stderr}"

        commit_output = result.stdout

        # Push to remote. Credentials are supplied per-op through the
        # environment (build_gitea_auth_env) — never persisted in origin and
        # never on argv — so neither the sandbox-mounted .git/config nor
        # /proc/<pid>/cmdline ever holds the token.
        if push:
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
                env=build_gitea_auth_env(),
            )

            if result.returncode != 0:
                # If push fails, commit is still local
                return (
                    False,
                    f"git push failed: {result.stderr}\nCommit succeeded locally: {commit_output}",
                )

            return True, f"✓ Committed and pushed to {branch}\n{commit_output}"

        return True, f"✓ Committed locally\n{commit_output}"

    except subprocess.TimeoutExpired:
        return False, "git push timeout"
    except Exception as e:
        logger.exception(f"Git operation failed for {project_dir}")
        return False, str(e)


def git_pull(project_dir: Path, branch: str = "develop") -> Tuple[bool, str]:
    """
    Pull latest changes from Gitea.

    Args:
        project_dir: Path to project directory
        branch: Branch to pull from

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        project_dir = Path(project_dir)

        if not (project_dir / ".git").exists():
            return False, f"Not a git repository: {project_dir}"

        # Fetch first. Credentials are injected per-op via the environment
        # (build_gitea_auth_env) so origin stays credential-less on disk.
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=build_gitea_auth_env(),
        )

        if result.returncode != 0:
            return False, f"git fetch failed: {result.stderr}"

        # Pull
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=build_gitea_auth_env(),
        )

        if result.returncode != 0:
            return False, f"git pull failed: {result.stderr}"

        return True, result.stdout

    except subprocess.TimeoutExpired:
        return False, "git pull timeout"
    except Exception as e:
        logger.exception(f"Git pull failed for {project_dir}")
        return False, str(e)


def sanitize_origin_url(project_dir: Path) -> bool:
    """Ensure the ``origin`` remote of ``project_dir`` is CREDENTIAL-LESS.

    SECURITY (sec-gitea-admin-token-plaintext-in-user-gitconfig): the previous
    ``configure_git_credentials()`` embedded ``http://<user>:<token>@host``
    into origin, persisting the platform Gitea ADMIN token into
    ``.git/config``. That file is bind-mounted read/write into the user's
    Apptainer console at ``/workspace``, so any tenant could
    ``cat /workspace/.git/config`` and recover the admin token — a
    cross-tenant repo takeover. Credentials are now supplied per-operation
    via :func:`build_gitea_auth_env` (never written to disk), so origin only
    ever needs the bare URL.

    This function therefore STRIPS any embedded credentials from origin (it
    also de-poisons repos cloned before the fix) and is idempotent — a clean
    origin is left untouched. It takes NO credential arguments by design: a
    function that never receives the token cannot re-introduce the leak.

    Args:
        project_dir: Path to the project's git working tree.

    Returns:
        True when origin is (now) credential-less, False on failure.
    """
    try:
        project_dir = Path(project_dir)

        # Get current remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Failed to get remote URL: {result.stderr}")
            return False

        origin_url = result.stdout.strip()

        if not origin_url.startswith("http"):
            # SSH or other transport — no HTTP token to strip.
            return True

        clean_url = strip_url_credentials(origin_url)
        if clean_url != origin_url:
            subprocess.run(
                ["git", "remote", "set-url", "origin", clean_url],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            logger.info(
                "✓ Sanitized origin URL (removed embedded credentials) for %s",
                project_dir,
            )
        return True

    except Exception as e:
        logger.error(f"Failed to sanitize git credentials: {e}")
        return False


def auto_commit_file(
    project_dir: Path, filepath: str, message: str = None
) -> Tuple[bool, str]:
    """
    Automatically commit and push a single file.

    Useful for Writer and Scholar modules when files are edited.

    Args:
        project_dir: Path to project directory
        filepath: Relative path to file (e.g., 'paper/manuscript.tex')
        message: Commit message (auto-generated if None)

    Returns:
        Tuple of (success: bool, output: str)

    Example:
        >>> # In Writer module after saving manuscript
        >>> auto_commit_file(
        ...     project.git_clone_path,
        ...     'paper/01_manuscript/main.tex',
        ...     'Update manuscript introduction'
        ... )
    """
    if message is None:
        message = f"Auto-save: {filepath}"

    return git_commit_and_push(
        project_dir=project_dir,
        message=message,
        files=[filepath],
        branch="develop",
        push=True,
    )


def init_git_repo_with_gitea_remote(
    local_dir: Path, gitea_clone_url: str, username: str, email: str
) -> bool:
    """
    Initialize a git repository and set up Gitea as remote.

    Args:
        local_dir: Path to local directory
        gitea_clone_url: Gitea clone URL
        username: Git user name
        email: Git user email

    Returns:
        True if successful
    """
    try:
        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=local_dir, capture_output=True, check=True)

        # Configure user
        subprocess.run(
            ["git", "config", "user.name", username],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "config", "user.email", email],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", gitea_clone_url],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initial commit"],
            cwd=local_dir,
            capture_output=True,
            check=True,
        )

        logger.info(f"✓ Initialized git repo with Gitea remote: {local_dir}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git initialization failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize git repo: {e}")
        return False


# EOF
