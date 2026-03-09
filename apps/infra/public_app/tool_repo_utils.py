#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository Concatenator Tool - Utility Functions

URL parsing and SSH key handling for Git repository operations.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _get_user_ssh_key(user) -> Optional[Path]:
    """
    Get user's SSH private key path.

    SSH keys are stored in user's home directory:
    ./data/users/{username}/.ssh/

    Returns path to private key if exists, None otherwise.
    """
    from django.conf import settings

    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    # Get user's home directory
    manager = get_project_filesystem_manager(user)
    user_home = manager.base_path.parent
    ssh_dir = user_home / ".ssh"

    logger.debug(f"SSH key lookup: user={user.username}, ssh_dir={ssh_dir}")

    if ssh_dir.exists():
        logger.debug(f"SSH dir contents: {list(ssh_dir.iterdir())}")
    else:
        logger.debug(f"Creating ssh_dir: {ssh_dir}")
        ssh_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(ssh_dir, 0o700)

    # Common SSH key types (in order of preference)
    ssh_key_names = ["id_ed25519", "id_rsa", "id_ecdsa"]

    for key_name in ssh_key_names:
        key_path = ssh_dir / key_name
        if key_path.exists():
            logger.debug(f"Found SSH key: {key_path}")
            return key_path

    # FALLBACK: Check old centralized location for backward compatibility
    old_ssh_dir = Path(settings.BASE_DIR) / "data" / "ssh_keys" / f"user_{user.id}"
    logger.debug(f"Checking old location: {old_ssh_dir}")

    if old_ssh_dir.exists():
        for key_name in ssh_key_names:
            old_key_path = old_ssh_dir / key_name
            if old_key_path.exists():
                logger.debug(f"Migrating key from old location: {old_key_path}")
                return _migrate_ssh_key(old_key_path, ssh_dir, key_name)

    logger.debug(f"No SSH key found for {user.username}")
    return None


def _migrate_ssh_key(old_key_path: Path, ssh_dir: Path, key_name: str) -> Path:
    """Migrate SSH key from old location to new user home directory."""
    import shutil

    new_key_path = ssh_dir / key_name
    new_pub_path = ssh_dir / f"{key_name}.pub"
    old_pub_path = old_key_path.parent / f"{key_name}.pub"

    shutil.copy2(old_key_path, new_key_path)
    if old_pub_path.exists():
        shutil.copy2(old_pub_path, new_pub_path)

    os.chmod(new_key_path, 0o600)
    if new_pub_path.exists():
        os.chmod(new_pub_path, 0o644)

    logger.debug(f"Migrated SSH key to {new_key_path}")
    return new_key_path


def _convert_https_to_ssh(https_url: str) -> str:
    """
    Convert HTTPS Git URL to SSH format.

    Examples:
    - https://github.com/user/repo.git -> git@github.com:user/repo.git
    - https://gitlab.com/user/repo.git -> git@gitlab.com:user/repo.git
    """
    providers = [
        (r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", "github.com"),
        (r"https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?$", "gitlab.com"),
        (r"https?://bitbucket\.org/([^/]+)/([^/]+?)(?:\.git)?$", "bitbucket.org"),
    ]

    for pattern, domain in providers:
        match = re.match(pattern, https_url)
        if match:
            user, repo = match.groups()
            return f"git@{domain}:{user}/{repo}.git"

    return https_url


def parse_github_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse GitHub URL to extract repo URL, branch, and subdirectory.

    Examples:
    - https://github.com/user/repo -> (https://github.com/user/repo.git, None, None)
    - https://github.com/user/repo/tree/main/path -> (url.git, main, path)
    - git@github.com:user/repo.git -> (git@github.com:user/repo.git, None, None)

    Returns: (git_url, branch, subdirectory)
    """
    # Handle SSH URLs
    if url.startswith("git@"):
        return (url, None, None)

    # GitHub pattern with subdirectory
    pattern = r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)/(.+))?"
    match = re.match(pattern, url)
    if match:
        user, repo, branch, subdir = match.groups()
        repo = repo.replace(".git", "")
        git_url = f"https://github.com/{user}/{repo}.git"
        return (git_url, branch, subdir)

    # GitLab pattern
    pattern_gitlab = r"https?://gitlab\.com/([^/]+)/([^/]+)(?:/-/tree/([^/]+)/(.+))?"
    match = re.match(pattern_gitlab, url)
    if match:
        user, repo, branch, subdir = match.groups()
        repo = repo.replace(".git", "")
        git_url = f"https://gitlab.com/{user}/{repo}.git"
        return (git_url, branch, subdir)

    # Simple URL without subdirectory
    if url.endswith(".git"):
        return (url, None, None)
    return (url + ".git", None, None)


# EOF
