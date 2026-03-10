"""Backward-compatible re-exports.

Canonical module: apps.infra.gitea_app.services.gitea_sync_service
"""

from apps.infra.gitea_app.services.gitea_sync_service import (  # noqa: F401
    ensure_gitea_user_exists,
    remove_ssh_key_from_gitea,
    sync_all_users_to_gitea,
    sync_ssh_key_to_gitea,
    sync_user_to_gitea,
)

# EOF
