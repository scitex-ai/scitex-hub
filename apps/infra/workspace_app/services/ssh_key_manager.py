#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 20:42:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/workspace_app/services/ssh_key_manager.py
# ----------------------------------------
"""
SSH key management for workspace SSH gateway.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import paramiko
from django.conf import settings

__FILE__ = "./apps/workspace_app/services/ssh_key_manager.py"
__DIR__ = os.path.dirname(__FILE__)

logger = logging.getLogger(__name__)


class SSHKeyManager:
    """
    Manage SSH host keys for the workspace gateway.
    """

    def __init__(self, key_dir: str | None = None):
        """
        Initialize SSH key manager.

        Args:
            key_dir: Directory to store SSH keys (defaults to settings.SSH_KEY_DIR)
        """
        self.key_dir = Path(
            key_dir or getattr(settings, "SSH_KEY_DIR", "/app/ssh_keys")
        )
        self.key_dir.mkdir(parents=True, exist_ok=True)

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
        key_path = self.get_host_key_path()

        if key_path.exists():
            try:
                logger.info(f"Loading SSH host key from: {key_path}")
                return paramiko.RSAKey.from_private_key_file(str(key_path))
            except Exception as e:
                logger.warning(f"Failed to load host key from {key_path}: {e}")
                logger.info("Generating new host key...")

        # Generate new key
        logger.info("Generating new SSH host key...")
        host_key = paramiko.RSAKey.generate(2048)

        # Save key
        try:
            host_key.write_private_key_file(str(key_path))
            # Set restrictive permissions
            os.chmod(key_path, 0o600)
            logger.info(f"SSH host key saved to: {key_path}")
        except Exception as e:
            logger.error(f"Failed to save host key to {key_path}: {e}")
            logger.warning(
                "Using ephemeral host key (will not persist across restarts)"
            )

        return host_key

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
