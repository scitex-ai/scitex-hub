#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository Concatenator Tool - Clone and Analyze API."""

from __future__ import annotations

import json
import logging
import os
import shutil
import shlex
import tempfile
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.git_source_safety import (
    GitSourceRejected,
    run_git_clone,
    validate_git_source,
)

from .tool_repo_utils import _convert_https_to_ssh, _get_user_ssh_key, parse_github_url

logger = logging.getLogger(__name__)

_SUPPORTED_HOSTS = ("github.com", "gitlab.com", "bitbucket.org")

# Store temp paths for cleanup (in production, use Redis/cache)
_temp_repos = {}


def get_temp_repos():
    """Get the temp repos dictionary for use in other modules."""
    return _temp_repos


@require_http_methods(["POST"])
def api_clone_and_analyze(request):
    """
    Clone a Git repository and analyze file extensions.

    POST data:
    - repo_url: Git repository URL (supports subdirectory URLs)
    - use_ssh: Whether to use SSH authentication (default: auto-detect)

    Returns:
    - temp_path: Path to cloned repository
    - extensions: List of file extensions found
    - file_count: Total number of files
    - subdirectory: Subdirectory path if specified
    - branch: Branch name if specified
    """
    try:
        data = json.loads(request.body)
        original_url = data.get("repo_url", "").strip()
        use_ssh = data.get("use_ssh", False)

        if not original_url:
            return JsonResponse({"error": "Repository URL is required"}, status=400)

        # Parse URL to extract git_url, branch, and subdirectory
        git_url, branch, subdirectory = parse_github_url(original_url)

        # Auto-convert HTTPS to SSH if user wants SSH
        if use_ssh and git_url.startswith("https://"):
            git_url = _convert_https_to_ssh(git_url)

        # Validate URL: exact supported host, public address, safe transport
        try:
            source = validate_git_source(
                git_url, ssh_hosts=_SUPPORTED_HOSTS, https_hosts=_SUPPORTED_HOSTS
            )
        except GitSourceRejected as exc:
            return JsonResponse({"error": f"Repository URL not accepted: {exc}"}, status=400)
        if source.host not in _SUPPORTED_HOSTS:
            return JsonResponse(
                {"error": "Only GitHub, GitLab, and Bitbucket URLs are supported"},
                status=400,
            )
        is_ssh = source.protocol == "ssh"
        if branch is not None and (not branch or branch.startswith("-")):
            return JsonResponse({"error": "Invalid branch name"}, status=400)

        # If using SSH, get user's SSH key
        ssh_key_path = None
        if is_ssh:
            result = _validate_ssh_auth(request, git_url)
            if isinstance(result, JsonResponse):
                return result
            ssh_key_path = result

        # Clone and analyze repository
        return _clone_repository(source, branch, subdirectory, ssh_key_path)

    except Exception as e:
        logger.error(f"Error in clone_and_analyze: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _validate_ssh_auth(request, git_url):
    """Validate SSH authentication for the request."""
    if request.user.is_authenticated:
        ssh_key_path = _get_user_ssh_key(request.user)
        if not ssh_key_path:
            return JsonResponse(
                {
                    "error": "SSH key not found in ~/.ssh/",
                    "help": (
                        "Please add your SSH key:\n"
                        "1. Generate key: ssh-keygen -t ed25519\n"
                        "2. Add to GitHub: https://github.com/settings/keys\n"
                        "3. Upload to SciTeX: Account Settings"
                    ),
                    "settings_url": f"/{request.user.username}/settings/",
                },
                status=400,
            )
        return ssh_key_path
    return JsonResponse(
        {"error": "Authentication required for SSH access. Please login."},
        status=401,
    )


def _clone_repository(source, branch, subdirectory, ssh_key_path):
    """Clone repository and analyze its contents."""
    temp_dir = tempfile.mkdtemp(prefix="scitex_repo_")
    temp_path = Path(temp_dir)

    try:
        extra_args = ["--depth", "1"]
        if branch:
            extra_args.append(f"--branch={branch}")

        # Setup SSH environment if needed
        env = os.environ.copy()
        if ssh_key_path:
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {shlex.quote(str(ssh_key_path))} "
                "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null"
            )

        # Clone into the (empty) temp dir
        ok, error_msg = run_git_clone(
            source, temp_path, env=env, extra_args=extra_args, timeout=60
        )
        if not ok:
            shutil.rmtree(temp_path, ignore_errors=True)
            if "timed out" in error_msg:
                return JsonResponse(
                    {"error": "Clone timeout (>60s). Repository may be too large."},
                    status=400,
                )
            return _handle_clone_error(error_msg)

        # Determine analysis path
        analysis_path = temp_path
        if subdirectory:
            subdir_path = (temp_path / subdirectory).resolve()
            if not subdir_path.is_relative_to(temp_path.resolve()) or not subdir_path.exists():
                shutil.rmtree(temp_path, ignore_errors=True)
                return JsonResponse(
                    {"error": f'Subdirectory "{subdirectory}" not found in repository'},
                    status=404,
                )
            analysis_path = subdir_path

        # Analyze file extensions
        extensions, file_count = _analyze_extensions(analysis_path)

        # Store temp path and metadata
        session_key = str(temp_path)
        _temp_repos[session_key] = {
            "temp_path": temp_path,
            "subdirectory": subdirectory,
            "branch": branch,
        }

        return JsonResponse(
            {
                "success": True,
                "temp_path": session_key,
                "extensions": sorted(list(extensions)),
                "file_count": file_count,
                "subdirectory": subdirectory,
                "branch": branch or "main",
            }
        )

    except Exception as e:
        shutil.rmtree(temp_path, ignore_errors=True)
        logger.error(f"Error cloning repository: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _handle_clone_error(stderr):
    """Handle git clone errors with appropriate messages."""
    error_msg = stderr[:500] if stderr else "Clone failed"

    auth_phrases = [
        "could not read username",
        "could not read password",
        "authentication failed",
        "permission denied",
    ]
    if any(phrase in error_msg.lower() for phrase in auth_phrases):
        return JsonResponse(
            {
                "error": "Authentication failed",
                "help": (
                    "Your SSH key may not be added to GitHub.\n\n"
                    "Add this public key to GitHub:\nhttps://github.com/settings/keys"
                ),
                "detail": error_msg,
            },
            status=403,
        )

    if "not found" in error_msg.lower() or "404" in error_msg:
        return JsonResponse(
            {
                "error": "Repository not found. Please check the URL.",
                "detail": error_msg,
            },
            status=404,
        )

    return JsonResponse({"error": f"Git clone failed: {error_msg}"}, status=400)


def _analyze_extensions(analysis_path):
    """Analyze file extensions in the given path."""
    extensions = set()
    file_count = 0
    ignore_patterns = {
        ".git",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".egg-info",
        "htmlcov",
        "venv",
        ".venv",
    }

    for file_path in analysis_path.rglob("*"):
        if file_path.is_file():
            if any(pattern in str(file_path) for pattern in ignore_patterns):
                continue
            ext = file_path.suffix.lower()
            if ext:
                extensions.add(ext)
            file_count += 1

    return extensions, file_count


# EOF
