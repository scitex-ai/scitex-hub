#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository Concatenator Tool - Clone and Analyze API."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .tool_repo_utils import _convert_https_to_ssh, _get_user_ssh_key, parse_github_url

logger = logging.getLogger(__name__)

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

        # Validate URL
        is_ssh = git_url.startswith("git@")
        supported_domains = ["github.com", "gitlab.com", "bitbucket.org"]
        if not is_ssh and not any(domain in git_url for domain in supported_domains):
            return JsonResponse(
                {"error": "Only GitHub, GitLab, and Bitbucket URLs are supported"},
                status=400,
            )

        # Auto-convert HTTPS to SSH if user wants SSH
        if use_ssh and not is_ssh and git_url.startswith("https://"):
            git_url = _convert_https_to_ssh(git_url)
            is_ssh = True

        # If using SSH, get user's SSH key
        ssh_key_path = None
        if is_ssh:
            result = _validate_ssh_auth(request, git_url)
            if isinstance(result, JsonResponse):
                return result
            ssh_key_path = result

        # Clone and analyze repository
        return _clone_repository(git_url, branch, subdirectory, ssh_key_path, is_ssh)

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


def _clone_repository(git_url, branch, subdirectory, ssh_key_path, is_ssh):
    """Clone repository and analyze its contents."""
    temp_dir = tempfile.mkdtemp(prefix="scitex_repo_")
    temp_path = Path(temp_dir)

    try:
        # Build git clone command
        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([git_url, str(temp_path)])

        # Setup SSH environment if needed
        env = os.environ.copy()
        if ssh_key_path:
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"
            )

        # Clone repository
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )

        if result.returncode != 0:
            shutil.rmtree(temp_path, ignore_errors=True)
            return _handle_clone_error(result.stderr)

        # Determine analysis path
        analysis_path = temp_path
        if subdirectory:
            subdir_path = temp_path / subdirectory
            if not subdir_path.exists():
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

    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_path, ignore_errors=True)
        return JsonResponse(
            {"error": "Clone timeout (>60s). Repository may be too large."}, status=400
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
