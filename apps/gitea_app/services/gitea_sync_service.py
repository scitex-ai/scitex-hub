#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 20:10:00 (ywatanabe)"
# File: ./apps/gitea_app/services/gitea_sync_service.py

"""
Gitea synchronization utilities for SciTeX Cloud

Canonical module for syncing Django users, SSH keys, and projects with Gitea.
"""

import logging
from typing import Optional, Tuple

from django.contrib.auth.models import User

from apps.gitea_app.api_client import GiteaClient
from apps.gitea_app.exceptions import (
    GiteaAPIError,
    GiteaConnectionError,
    GiteaUserCreationError,
)

logger = logging.getLogger(__name__)


def sync_user_to_gitea(user: User, password: Optional[str] = None) -> bool:
    """
    Create or update a Gitea user account for a Django user.

    Args:
        user: Django User instance
        password: User's password (required for new user creation)

    Returns:
        True if successful, False otherwise
    """
    try:
        client = GiteaClient()

        if client.user_exists(user.username):
            logger.info(f"Gitea user already exists: {user.username}")
            return True

        if not password:
            logger.warning(
                f"Cannot create Gitea user {user.username}: password required"
            )
            return False

        client.create_user(
            username=user.username,
            email=user.email,
            password=password,
            must_change_password=False,
        )

        logger.info(f"Created Gitea user: {user.username}")
        return True

    except Exception as e:
        logger.error(f"Failed to sync user {user.username} to Gitea: {e}")
        return False


def sync_all_users_to_gitea():
    """
    Sync all Django users to Gitea.

    Note: Cannot sync passwords (they're hashed in Django).
    Users will need to set Gitea passwords separately or use OAuth.
    """
    from django.contrib.auth.models import User

    users = User.objects.filter(is_active=True)
    success_count = 0
    failed_count = 0

    for user in users:
        if sync_user_to_gitea(user):
            success_count += 1
        else:
            failed_count += 1

    logger.info(f"User sync complete: {success_count} succeeded, {failed_count} failed")
    return success_count, failed_count


def ensure_gitea_user_exists(user: User) -> bool:
    """
    Ensure a Gitea user exists before creating repositories.
    Auto-creates the Gitea user if missing.

    Args:
        user: Django User instance

    Returns:
        True if user exists or was created successfully

    Raises:
        GiteaUserCreationError: If user creation fails
        GiteaConnectionError: If cannot connect to Gitea
    """
    try:
        client = GiteaClient()
    except Exception as e:
        error_msg = f"Cannot initialize Gitea client: {str(e)}"
        logger.error(error_msg)
        raise GiteaConnectionError(error_msg)

    if client.user_exists(user.username):
        logger.info(f"Gitea user already exists: {user.username}")
        return True

    logger.info(f"Gitea user not found, creating: {user.username}")

    import secrets

    random_password = secrets.token_urlsafe(32)

    try:
        client.create_user(
            username=user.username,
            email=user.email,
            password=random_password,
            must_change_password=False,
        )
        logger.info(f"Created Gitea user: {user.username}")
        return True
    except GiteaAPIError as e:
        error_msg = f"Gitea API error during user creation: {str(e)}"
        logger.error(error_msg)
        raise GiteaUserCreationError(user.username, error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during user creation: {str(e)}"
        logger.error(error_msg)
        raise GiteaUserCreationError(user.username, error_msg)


def sync_ssh_key_to_gitea(user: User) -> Tuple[bool, Optional[str]]:
    """
    Sync user's SSH key from SciTeX to Gitea.

    Args:
        user: Django User instance

    Returns:
        Tuple of (success, error_message)
    """
    try:
        from apps.accounts_app.models import UserProfile

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return False, "User profile not found"

        if not profile.ssh_public_key:
            return False, "No SSH key found for user"

        client = GiteaClient()

        fingerprint = profile.ssh_key_fingerprint
        if fingerprint:
            parts = fingerprint.split()
            sha256_hash = None
            for part in parts:
                if part.startswith("SHA256:"):
                    sha256_hash = part.replace("SHA256:", "")
                    break

            if sha256_hash:
                existing_key = client.find_ssh_key_by_fingerprint(
                    sha256_hash, user.username
                )
                if existing_key:
                    logger.info(
                        f"SSH key already exists in Gitea for user: {user.username}"
                    )
                    return True, None

        title = f"SciTeX Cloud Key ({user.username})"
        client.add_ssh_key(
            title=title, key=profile.ssh_public_key, username=user.username
        )

        logger.info(f"Synced SSH key to Gitea for user: {user.username}")
        return True, None

    except GiteaAPIError as e:
        error_msg = f"Gitea API error: {str(e)}"
        logger.error(f"Failed to sync SSH key for {user.username}: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to sync SSH key for {user.username}: {error_msg}")
        return False, error_msg


def remove_ssh_key_from_gitea(user: User) -> Tuple[bool, Optional[str]]:
    """
    Remove user's SSH key from Gitea.

    Args:
        user: Django User instance

    Returns:
        Tuple of (success, error_message)
    """
    try:
        from apps.accounts_app.models import UserProfile

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return True, None

        if not profile.ssh_key_fingerprint:
            return True, None

        client = GiteaClient()

        parts = profile.ssh_key_fingerprint.split()
        sha256_hash = None
        for part in parts:
            if part.startswith("SHA256:"):
                sha256_hash = part.replace("SHA256:", "")
                break

        if not sha256_hash:
            return True, None

        existing_key = client.find_ssh_key_by_fingerprint(sha256_hash, user.username)
        if existing_key:
            key_id = existing_key.get("id")
            if key_id:
                client.delete_ssh_key(key_id, user.username)
                logger.info(f"Removed SSH key from Gitea for user: {user.username}")

        return True, None

    except GiteaAPIError as e:
        error_msg = f"Gitea API error: {str(e)}"
        logger.error(f"Failed to remove SSH key for {user.username}: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to remove SSH key for {user.username}: {error_msg}")
        return False, error_msg


# EOF
