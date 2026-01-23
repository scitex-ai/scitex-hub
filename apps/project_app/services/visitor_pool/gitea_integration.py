"""
Gitea Integration for Visitor Pool

Manages creation and synchronization of visitor users in Gitea.
"""

import logging
import secrets

logger = logging.getLogger(__name__)


class GiteaIntegration:
    """Handles Gitea integration for visitor accounts."""

    VISITOR_USER_PREFIX = "visitor-"

    @classmethod
    def ensure_gitea_users_exist(cls, pool_size: int):
        """
        Ensure all visitor users exist in Gitea for Git SSH access.

        This is idempotent - safe to call multiple times.

        Args:
            pool_size: Number of visitor accounts in pool
        """
        try:
            from apps.gitea_app.api_client import GiteaClient
            client = GiteaClient()

            for i in range(1, pool_size + 1):
                visitor_num = f"{i:03d}"
                username = f"{cls.VISITOR_USER_PREFIX}{visitor_num}"
                cls.ensure_user_in_gitea(username, visitor_num, client)

        except Exception as e:
            logger.warning(f"[VisitorPool] Failed to ensure Gitea users: {e}")

    @classmethod
    def ensure_user_in_gitea(cls, username: str, visitor_num: str, client=None):
        """
        Ensure a single visitor user exists in Gitea.

        Args:
            username: Username for the visitor
            visitor_num: Numeric identifier (e.g., "001")
            client: Optional GiteaClient instance (created if not provided)
        """
        if client is None:
            try:
                from apps.gitea_app.api_client import GiteaClient
                client = GiteaClient()
            except Exception as e:
                logger.warning(f"[VisitorPool] Failed to initialize Gitea client: {e}")
                return

        try:
            # Check if user exists in Gitea
            try:
                client._request("GET", f"/users/{username}")
                logger.debug(f"[VisitorPool] Gitea user already exists: {username}")
            except Exception:
                # User doesn't exist, create it
                cls._create_gitea_user(client, username, visitor_num)

        except Exception as e:
            logger.warning(f"[VisitorPool] Failed to ensure Gitea user {username}: {e}")

    @classmethod
    def _create_gitea_user(cls, client, username: str, visitor_num: str):
        """Create a new user in Gitea."""
        visitor_password = secrets.token_urlsafe(32)  # Random password, never to be used
        user_data = {
            "username": username,
            "email": f"{username}@visitor.scitex.local",
            "password": visitor_password,
            "full_name": f"Visitor {visitor_num}",
            "send_notify": False,
            "must_change_password": False,
        }
        client._request("POST", "/admin/users", json=user_data)
        logger.info(f"[VisitorPool] Created Gitea user: {username}")
