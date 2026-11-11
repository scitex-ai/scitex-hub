#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 20:42:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/workspace_app/services/ssh_key_manager.py
# ----------------------------------------
"""
SSH key management for workspace SSH gateway.
"""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile

import paramiko
from django.conf import settings

__FILE__ = "./apps/workspace_app/services/ssh_key_manager.py"
__DIR__ = os.path.dirname(__FILE__)


class SSHKeyManager:
    """
    Manage SSH host keys for the workspace gateway.
    """

    def __init__(self, key_dir: str | Path | None = None):
        """
        Initialize SSH key manager.

        Args:
            key_dir: Explicit key directory, otherwise the host SSH_KEY_DIR
                setting or the deployment's persistent hub runtime state.
        """
        selected = (
            key_dir if key_dir is not None else getattr(settings, "SSH_KEY_DIR", None)
        )
        if selected is None or selected == "":
            from scitex_config._ecosystem import local_state

            selected = local_state.runtime_path("hub") / "ssh"
        self.key_dir = Path(selected)
        self.key_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def get_host_key_path(self) -> Path:
        """
        Get path to SSH host key.

        Returns:
            Path to host key file
        """
        return self.key_dir / "ssh_host_rsa_key"

    def load_or_generate_host_key(self) -> paramiko.RSAKey:
        """
        Load existing host key or generate a new one.

        Returns:
            paramiko.RSAKey: SSH host key
        """
        try:
            return self._read_host_key()
        except FileNotFoundError:
            # Only absence admits creation. Existing unreadable, corrupt or
            # symbolic keys must never turn into another server identity.
            return self._publish_host_key()

    def _read_host_key(self) -> paramiko.RSAKey:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(self.get_host_key_path(), flags), "r") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError("SSH host key must be a regular private file")
            mode = stat.S_IMODE(metadata.st_mode)
            if mode & 0o077 or not mode & 0o400:
                raise PermissionError(
                    "SSH host key must be owner-readable with no group/other access"
                )
            return paramiko.RSAKey.from_private_key(stream)

    def _publish_host_key(self) -> paramiko.RSAKey:
        """Publish one complete private key without replacing a racing peer."""
        host_key = paramiko.RSAKey.generate(2048)
        descriptor, temporary = tempfile.mkstemp(
            prefix=".ssh-host-key-", dir=self.key_dir
        )
        try:
            with os.fdopen(descriptor, "w") as stream:
                host_key.write_private_key(stream)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Exclusive atomic publication: readers see the complete key,
                # and concurrent initializers all reopen the winner.
                os.link(temporary, self.get_host_key_path())
            except FileExistsError:
                return self._read_host_key()
            directory_fd = os.open(self.key_dir, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return host_key
        finally:
            os.unlink(temporary)

    def get_host_key_fingerprint(self, host_key: paramiko.RSAKey) -> str:
        """
        Get SSH host key fingerprint.

        Args:
            host_key: SSH host key

        Returns:
            Fingerprint string (SHA256 format)
        """
        import base64
        import hashlib

        key_bytes = host_key.asbytes()
        hash_obj = hashlib.sha256(key_bytes)
        fingerprint = base64.b64encode(hash_obj.digest()).decode().rstrip("=")
        return f"SHA256:{fingerprint}"

    def export_public_key(self, host_key: paramiko.RSAKey) -> str:
        """
        Export public key in OpenSSH format.

        Args:
            host_key: SSH host key

        Returns:
            Public key string
        """
        return f"ssh-rsa {host_key.get_base64()}"


# EOF
