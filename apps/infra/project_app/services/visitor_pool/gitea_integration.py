"""
Gitea Integration for Visitor Pool

Manages creation and synchronization of visitor users in Gitea.
"""

import logging
import os
import secrets

logger = logging.getLogger(__name__)


class GiteaIntegration:
    """Handles Gitea integration for visitor accounts."""

    VISITOR_USER_PREFIX = "visitor-"

    @staticmethod
    def _gitea_enabled() -> bool:
        """Whether visitor Gitea provisioning is enabled.

        Defaults to True (prod/staging). Set
        ``SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED=false`` on environments with no
        Gitea backend (e.g. the dev preview stack) so the visitor pool can
        allocate slots without Gitea — visitors then get a workspace but no git
        SSH access, which is correct for a browse-only demo. This is an explicit,
        logged opt-out, not a silent fallback: when disabled we WARN and skip.
        """
        return os.environ.get(
            "SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED", "true"
        ).strip().lower() in ("1", "true", "yes", "on")

    @classmethod
    def ensure_gitea_users_exist(cls, pool_size: int):
        """
        Ensure all visitor users exist in Gitea for Git SSH access.

        This is idempotent - safe to call multiple times.

        Args:
            pool_size: Number of visitor accounts in pool

        Raises:
            GiteaConnectionError: If Gitea client cannot be initialized
            GiteaAPIError: If user creation fails
        """
        if not cls._gitea_enabled():
            logger.warning(
                "[VisitorPool] Gitea provisioning disabled "
                "(SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED=false); skipping visitor "
                "Gitea user creation — visitors get no git SSH access (dev/no-Gitea)."
            )
            return

        from apps.infra.gitea_app.api_client import GiteaClient

        client = GiteaClient()

        for i in range(1, pool_size + 1):
            visitor_num = f"{i:03d}"
            username = f"{cls.VISITOR_USER_PREFIX}{visitor_num}"
            cls.ensure_user_in_gitea(username, visitor_num, client)

    @classmethod
    def ensure_user_in_gitea(cls, username: str, visitor_num: str, client=None):
        """
        Ensure a single visitor user exists in Gitea.

        Args:
            username: Username for the visitor
            visitor_num: Numeric identifier (e.g., "001")
            client: Optional GiteaClient instance (created if not provided)

        Raises:
            GiteaConnectionError: If Gitea client cannot be initialized
            GiteaAPIError: If user check or creation fails
        """
        if not cls._gitea_enabled():
            logger.warning(
                "[VisitorPool] Gitea provisioning disabled; skipping Gitea user "
                f"for {username} (dev/no-Gitea)."
            )
            return

        if client is None:
            from apps.infra.gitea_app.api_client import GiteaClient

            client = GiteaClient()

        if client.user_exists(username):
            logger.debug(f"[VisitorPool] Gitea user already exists: {username}")
        else:
            cls._create_gitea_user(client, username, visitor_num)

    @classmethod
    def _create_gitea_user(cls, client, username: str, visitor_num: str):
        """Create a new user in Gitea."""
        visitor_password = secrets.token_urlsafe(32)
        client.create_user(
            username=username,
            email=f"{username}@visitor.scitex.local",
            password=visitor_password,
            must_change_password=False,
        )
        logger.info(f"[VisitorPool] Created Gitea user: {username}")
