"""Paramiko SSH server interface for the SSH gateway.

Public-key authentication only. Keys are the ones a user registered in the
Hub (``WorkspaceSSHKey``, managed at /accounts/settings/ssh-keys/).

paramiko hands every ``password`` and ``keyboard-interactive`` userauth
request to ``check_auth_password`` / ``check_auth_interactive`` whatever
``get_allowed_auths`` advertises, so both refuse explicitly. Interactive
shells only: ``exec``/``subsystem`` requests (remote commands, scp, sftp)
are refused until they can be routed into the user's allocation.
"""

from __future__ import annotations

import logging
import re
import threading

import paramiko

from .throttle import GatewayThrottle

logger = logging.getLogger(__name__)
auth_log = logging.getLogger("scitex_hub.ssh_gateway.auth")

_SAFE = re.compile(r"[^A-Za-z0-9._@+-]")


def safe_field(value, limit: int = 64) -> str:
    """Client-supplied text made safe for a single log line."""
    text = value if isinstance(value, str) else repr(value)
    return _SAFE.sub("?", text)[:limit] or "-"


def log_auth_event(event: str, source: str, username=None, **fields) -> None:
    """One structured line per authentication event (grep/fail2ban friendly)."""
    parts = [f"ssh_auth event={event}", f"src={safe_field(source)}"]
    if username is not None:
        parts.append(f"user={safe_field(username)}")
    for key, value in fields.items():
        parts.append(f"{key}={safe_field(value, 128)}")
    auth_log.info(" ".join(parts))


class SSHGateway(paramiko.ServerInterface):
    """SSH server interface: registered public keys open a shell."""

    def __init__(self, source: str = "-", throttle: GatewayThrottle | None = None):
        super().__init__()
        self.source = source
        self.throttle = throttle
        self.username = None
        self.user = None
        self.key_title = None
        self.auth_attempts = 0
        self.attempted_username = None
        self.event = threading.Event()
        self.pty_width = 80
        self.pty_height = 24
        self._broker_client = None

    # -- authentication -----------------------------------------------------
    def _over_attempt_budget(self) -> bool:
        limit = (
            self.throttle.config.max_auth_attempts_per_connection
            if self.throttle
            else 12
        )
        return self.auth_attempts > limit

    def check_auth_none(self, username: str) -> int:
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username: str, password: str) -> int:
        self.attempted_username = username
        log_auth_event("refused", self.source, username, method="password")
        return paramiko.AUTH_FAILED

    def check_auth_interactive(self, username: str, submethods: str) -> int:
        self.attempted_username = username
        log_auth_event("refused", self.source, username, method="keyboard-interactive")
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        """Accept a key registered by an active user.

        paramiko calls this first for the "is this key acceptable?" probe and
        again with the signature, and verifies the signature itself after a
        success. A shell starts only after the transport reports the
        connection authenticated (see client_handler).
        """
        self.auth_attempts += 1
        self.attempted_username = username
        if self._over_attempt_budget():
            log_auth_event("too-many-attempts", self.source, username)
            return paramiko.AUTH_FAILED
        if self.throttle and self.throttle.username_banned(username):
            log_auth_event("refused", self.source, username, reason="user-banned")
            return paramiko.AUTH_FAILED
        try:
            from django.contrib.auth import get_user_model

            from apps.infra.accounts_app.models import WorkspaceSSHKey
            from apps.infra.accounts_app.utils.ssh_key_validator import SSHKeyValidator

            fingerprint = SSHKeyValidator.calculate_fingerprint(
                f"{key.get_name()} {key.get_base64()}"
            )
            user = (
                get_user_model()
                .objects.filter(username=username, is_active=True)
                .first()
            )
            match = (
                WorkspaceSSHKey.objects.filter(
                    user=user, fingerprint=fingerprint
                ).first()
                if user is not None
                else None
            )
        except Exception:
            logger.exception("Public key lookup failed")
            return paramiko.AUTH_FAILED

        if match is None:
            # Same answer for "no such user" and "wrong key": no enumeration.
            log_auth_event(
                "key-rejected", self.source, username, fingerprint=fingerprint
            )
            return paramiko.AUTH_FAILED

        self.user = user
        self.username = username
        self.key_title = match.title
        log_auth_event("key-accepted", self.source, username, fingerprint=fingerprint)
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username: str) -> str:
        return "publickey"

    # -- channels -----------------------------------------------------------
    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        self.event.set()
        return True

    def check_channel_exec_request(self, channel, command) -> bool:
        log_auth_event("exec-refused", self.source, self.username)
        return False

    def check_channel_subsystem_request(self, channel, name) -> bool:
        log_auth_event("subsystem-refused", self.source, self.username, name=name)
        return False

    def check_port_forward_request(self, address, port):
        return False

    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

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


# EOF
