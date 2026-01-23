#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visitor User Storage Management

Provides temporary storage for visitor users using /tmp directory.
Sessions expire after a configured time period and are automatically cleaned up.
"""

from __future__ import annotations
import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration
VISITOR_STORAGE_ROOT = getattr(
    settings, "VISITOR_STORAGE_ROOT", "/tmp/scitex_visitor"
)
SESSION_EXPIRY_HOURS = getattr(settings, "VISITOR_SESSION_EXPIRY_HOURS", 24)


def get_visitor_storage_path(session_key: str) -> str:
    """
    Get or create storage path for visitor session.

    Args:
        session_key: Django session key

    Returns:
        Absolute path to visitor user's storage directory
    """
    if not session_key:
        raise ValueError("Session key is required for visitor storage")

    path = os.path.join(VISITOR_STORAGE_ROOT, session_key)
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "uploads"), exist_ok=True)

    # Create metadata on first access
    metadata_path = os.path.join(path, "metadata.json")
    if not os.path.exists(metadata_path):
        metadata = {
            "created_at": datetime.now().isoformat(),
            "expires_at": (
                datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
            ).isoformat(),
            "session_key": session_key,
            "last_accessed": datetime.now().isoformat(),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Created visitor storage for session {session_key[:8]}...")
    else:
        # Update last accessed time
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            metadata["last_accessed"] = datetime.now().isoformat()
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(
                f"Failed to update last_accessed for session {session_key[:8]}...: {e}"
            )

    return path


def save_session_data(session_key: str, data: dict) -> bool:
    """
    Save data to visitor user's session storage.

    Args:
        session_key: Django session key
        data: Dictionary of data to save

    Returns:
        True if successful, False otherwise
    """
    try:
        storage_path = get_visitor_storage_path(session_key)
        data_path = os.path.join(storage_path, "scholar_data.json")

        with open(data_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved session data for {session_key[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to save session data: {e}")
        return False


def load_session_data(session_key: str) -> Optional[dict]:
    """
    Load data from visitor user's session storage.

    Args:
        session_key: Django session key

    Returns:
        Dictionary of stored data, or None if not found
    """
    try:
        storage_path = os.path.join(VISITOR_STORAGE_ROOT, session_key)
        data_path = os.path.join(storage_path, "scholar_data.json")

        if os.path.exists(data_path):
            with open(data_path, "r") as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Failed to load session data: {e}")
        return None


def cleanup_expired_sessions() -> Tuple[int, int]:
    """
    Remove expired visitor sessions.

    Returns:
        Tuple of (cleaned_count, error_count)
    """
    if not os.path.exists(VISITOR_STORAGE_ROOT):
        logger.info("Visitor storage root does not exist, skipping cleanup")
        return (0, 0)

    cleaned = 0
    errors = 0
    now = datetime.now()

    logger.info(f"Starting cleanup of visitor sessions in {VISITOR_STORAGE_ROOT}")

    for session_dir in os.listdir(VISITOR_STORAGE_ROOT):
        session_path = os.path.join(VISITOR_STORAGE_ROOT, session_dir)
        metadata_path = os.path.join(session_path, "metadata.json")

        try:
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                expires_at = datetime.fromisoformat(metadata["expires_at"])

                if now > expires_at:
                    shutil.rmtree(session_path)
                    cleaned += 1
                    logger.info(
                        f"Cleaned up expired session: {session_dir[:8]}... (expired {(now - expires_at).days} days ago)"
                    )
            else:
                # No metadata file - clean up orphaned directory
                logger.warning(
                    f"No metadata found for {session_dir[:8]}..., removing orphaned directory"
                )
                shutil.rmtree(session_path)
                cleaned += 1

        except Exception as e:
            logger.error(f"Error cleaning up session {session_dir[:8]}...: {e}")
            errors += 1

    logger.info(f"Cleanup complete: {cleaned} sessions cleaned, {errors} errors")
    return (cleaned, errors)


def migrate_to_user_storage(session_key: str, user) -> bool:
    """
    Move visitor session data to user's permanent storage on signup.

    Args:
        session_key: Django session key
        user: Django User object

    Returns:
        True if migration successful, False otherwise
    """
    visitor_path = os.path.join(VISITOR_STORAGE_ROOT, session_key)

    if not os.path.exists(visitor_path):
        logger.info(f"No visitor data to migrate for session {session_key[:8]}...")
        return False

    try:
        # Define user's project path
        user_base = f"/data/users/{user.username}"
        user_proj_path = f"{user_base}/proj"

        # Create user directories if they don't exist
        os.makedirs(user_proj_path, exist_ok=True)

        # Create a "from_visitor" project
        import_project_path = os.path.join(user_proj_path, "imported_session")
        os.makedirs(import_project_path, exist_ok=True)

        # Move files (excluding metadata)
        migrated_files = []
        for item in os.listdir(visitor_path):
            if item == "metadata.json":
                continue

            src = os.path.join(visitor_path, item)
            dst = os.path.join(import_project_path, item)

            if os.path.exists(dst):
                # Handle name collision - add timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.splitext(item)[0]
                ext = os.path.splitext(item)[1]
                dst = os.path.join(import_project_path, f"{base_name}_{timestamp}{ext}")

            shutil.move(src, dst)
            migrated_files.append(item)

        # Clean up visitor directory
        shutil.rmtree(visitor_path)

        logger.info(
            f"Migrated {len(migrated_files)} items from session {session_key[:8]}... to user {user.username}"
        )
        logger.info(f"Files available at: {import_project_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to migrate visitor session to user storage: {e}")
        return False


def get_session_info(session_key: str) -> Optional[dict]:
    """
    Get metadata about an visitor session.

    Args:
        session_key: Django session key

    Returns:
        Dictionary with session metadata, or None if not found
    """
    try:
        metadata_path = os.path.join(
            VISITOR_STORAGE_ROOT, session_key, "metadata.json"
        )
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return None


def delete_visitor_session(session_key: str) -> bool:
    """
    Delete an visitor user's session data.

    Args:
        session_key: Django session key

    Returns:
        True if successful, False otherwise
    """
    try:
        session_path = os.path.join(VISITOR_STORAGE_ROOT, session_key)
        if os.path.exists(session_path):
            shutil.rmtree(session_path)
            logger.info(f"Deleted visitor session: {session_key[:8]}...")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete visitor session: {e}")
        return False


# EOF
