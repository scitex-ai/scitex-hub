"""Paramiko SSH server interface for the SSH gateway.

Supports pubkey auth (full shell) and password auth (key registration only).
"""

import logging
import threading

import paramiko
from django.contrib.auth import authenticate

from .key_registration import handle_ssh_copy_id

logger = logging.getLogger(__name__)


class SSHGateway(paramiko.ServerInterface):
    """SSH server with pubkey for shell, password for key registration."""

    def __init__(self):
        super().__init__()
        self.username = None
        self.user = None
        self.event = threading.Event()
        self.auth_method = None  # "publickey" or "password"
        self.pty_width = 80
        self.pty_height = 24
        self._broker_client = None

    def check_auth_password(self, username: str, password: str) -> int:
        logger.info(f"Password auth attempt for user: {username}")
        try:
            user = authenticate(username=username, password=password)
            if user and user.is_active:
                self.user = user
                self.username = username
                self.auth_method = "password"
                logger.info(f"Password auth successful for user: {username}")
                return paramiko.AUTH_SUCCESSFUL
        except Exception as e:
            logger.error(f"Password auth error for user {username}: {e}")
        logger.warning(f"Password auth failed for user: {username}")
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        logger.info(f"Public key auth attempt for user: {username}")
        try:
            from django.contrib.auth import get_user_model

            from apps.infra.accounts_app.models import WorkspaceSSHKey
            from apps.infra.accounts_app.utils.ssh_key_validator import SSHKeyValidator

            User = get_user_model()
            try:
                user = User.objects.get(username=username, is_active=True)
            except User.DoesNotExist:
                logger.warning(f"User not found: {username}")
                return paramiko.AUTH_FAILED

            key_type = key.get_name()
            key_data = key.get_base64()
            provided_key_str = f"{key_type} {key_data}"
            provided_fingerprint = SSHKeyValidator.calculate_fingerprint(
                provided_key_str
            )

            workspace_keys = WorkspaceSSHKey.objects.filter(
                user=user, fingerprint=provided_fingerprint
            )
            if workspace_keys.exists():
                workspace_key = workspace_keys.first()
                from django.utils import timezone

                workspace_key.last_used_at = timezone.now()
                workspace_key.save(update_fields=["last_used_at"])
                self.user = user
                self.username = username
                self.auth_method = "publickey"
                logger.info(
                    f"Public key auth successful: {username} "
                    f"(key: {workspace_key.title})"
                )
                return paramiko.AUTH_SUCCESSFUL

            logger.warning(f"Public key auth failed: {username} (no matching key)")
            return paramiko.AUTH_FAILED
        except Exception as e:
            logger.error(f"Public key auth error for {username}: {e}", exc_info=True)
            return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "publickey,password"

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        logger.info(f"Shell request for user: {self.username}")
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ) -> bool:
        self.pty_width = width
        self.pty_height = height
        return True

    def check_channel_window_change_request(
        self, channel, width, height, pixelwidth, pixelheight
    ):
        self.pty_width = width
        self.pty_height = height
        if self._broker_client and self._broker_client.session_id:
            try:
                self._broker_client.resize(height, width)
            except Exception as e:
                logger.debug(f"Resize forward error: {e}")
        return True

    def check_channel_exec_request(self, channel, command):
        """Handle exec requests — supports ssh-copy-id key upload."""
        cmd_str = command.decode("utf-8", errors="replace").strip()
        logger.info(f"Exec request from {self.username}: {cmd_str}")

        if "authorized_keys" in cmd_str or ".ssh" in cmd_str:
            threading.Thread(
                target=handle_ssh_copy_id,
                args=(channel, cmd_str, self.user),
                daemon=True,
            ).start()
            return True
        return False


# EOF
