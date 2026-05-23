#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-18 23:50:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/workspace_app/ssh_manager.py
# ----------------------------------------
"""
SSH Key Management for SciTeX Cloud

Handles SSH key generation, storage, and usage for Git operations.
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone


class SSHKeyManager:
    """Manage SSH keys for Git operations."""

    def __init__(self, user: User):
        self.user = user
        self.ssh_dir = Path(settings.BASE_DIR) / "data" / "ssh_keys" / f"user_{user.id}"
        self.private_key_path = self.ssh_dir / "id_rsa"
        self.public_key_path = self.ssh_dir / "id_rsa.pub"

    def get_or_create_user_key(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get or create SSH key pair for user.

        Returns:
            Tuple of (success, public_key_content, error_message)
        """
        # Check if key already exists
        if self.private_key_path.exists() and self.public_key_path.exists():
            try:
                public_key = self.public_key_path.read_text()
                return True, public_key, None
            except Exception as e:
                return False, None, str(e)

        # Create SSH directory with secure permissions
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.ssh_dir, 0o700)

        # Generate new key pair
        try:
            email_comment = self.user.email or f"{self.user.username}@scitex.ai"

            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "rsa",
                    "-b",
                    "4096",
                    "-C",
                    email_comment,
                    "-f",
                    str(self.private_key_path),
                    "-N",
                    "",  # No passphrase for automation
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            # Set proper permissions
            os.chmod(self.private_key_path, 0o600)
            os.chmod(self.public_key_path, 0o644)

            # Read public key
            public_key = self.public_key_path.read_text()

            # Get fingerprint
            fingerprint_result = subprocess.run(
                ["ssh-keygen", "-lf", str(self.public_key_path), "-E", "sha256"],
                capture_output=True,
                text=True,
                check=True,
            )
            fingerprint = fingerprint_result.stdout.strip()

            # Update user profile
            from apps.infra.accounts_app.models import UserProfile

            profile, _ = UserProfile.objects.get_or_create(user=self.user)
            profile.ssh_public_key = public_key
            profile.ssh_key_fingerprint = fingerprint
            profile.ssh_key_created_at = timezone.now()
            profile.save()

            return True, public_key, None

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            return False, None, f"Failed to generate SSH key: {error_msg}"
        except Exception as e:
            return False, None, str(e)

    def get_public_key(self) -> Optional[str]:
        """Get user's public SSH key."""
        try:
            if self.public_key_path.exists():
                return self.public_key_path.read_text()
            # Try to get from database
            from apps.infra.accounts_app.models import UserProfile

            try:
                profile = UserProfile.objects.get(user=self.user)
                return profile.ssh_public_key
            except UserProfile.DoesNotExist:
                return None
        except Exception:
            return None

    def get_private_key_path(self) -> Optional[Path]:
        """Get path to user's private SSH key."""
        return self.private_key_path if self.private_key_path.exists() else None

    def delete_user_key(self) -> Tuple[bool, Optional[str]]:
        """Delete user's SSH key pair."""
        try:
            import shutil

            if self.ssh_dir.exists():
                shutil.rmtree(self.ssh_dir)

            # Update database
            from apps.infra.accounts_app.models import UserProfile

            try:
                profile = UserProfile.objects.get(user=self.user)
                profile.ssh_public_key = (
                    ""  # CharField with blank=True requires empty string, not None
                )
                profile.ssh_key_fingerprint = (
                    ""  # CharField with blank=True requires empty string, not None
                )
                profile.ssh_key_created_at = (
                    None  # DateTimeField with null=True can be None
                )
                profile.ssh_key_last_used_at = (
                    None  # DateTimeField with null=True can be None
                )
                profile.save()
            except UserProfile.DoesNotExist:
                pass

            return True, None
        except Exception as e:
            return False, str(e)

    def mark_key_used(self):
        """Update last_used_at timestamp for the SSH key."""
        try:
            from apps.infra.accounts_app.models import UserProfile

            profile = UserProfile.objects.get(user=self.user)
            profile.ssh_key_last_used_at = timezone.now()
            profile.save(update_fields=["ssh_key_last_used_at"])
        except UserProfile.DoesNotExist:
            pass

    def has_ssh_key(self) -> bool:
        """Check if user has an SSH key configured."""
        return self.private_key_path.exists() and self.public_key_path.exists()

    def get_ssh_env(self) -> dict:
        """
        Get environment variables for Git SSH operations.

        Returns:
            dict: Environment variables to use with subprocess
        """
        env = os.environ.copy()

        if self.has_ssh_key():
            # Use GIT_SSH_COMMAND to specify SSH key and options
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {self.private_key_path} "
                f"-o StrictHostKeyChecking=accept-new "
                f"-o UserKnownHostsFile=/dev/null"
            )

        return env


# EOF
