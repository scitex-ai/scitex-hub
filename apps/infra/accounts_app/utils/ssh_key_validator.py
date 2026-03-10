#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 21:45:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/accounts_app/utils/ssh_key_validator.py
# ----------------------------------------
"""
SSH public key validation and fingerprint calculation.
"""

from __future__ import annotations

import base64
import hashlib
import re
from typing import Tuple


class SSHKeyValidator:
    """Validate and parse SSH public keys."""

    # Supported key types
    SUPPORTED_KEY_TYPES = [
        "ssh-rsa",
        "ssh-dss",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-ed25519",
    ]

    @classmethod
    def validate_public_key(cls, public_key: str) -> Tuple[bool, str, str]:
        """
        Validate an SSH public key.

        Args:
            public_key: SSH public key string

        Returns:
            Tuple of (is_valid, key_type, error_message)
        """
        if not public_key or not isinstance(public_key, str):
            return False, "", "Public key cannot be empty"

        # Clean the key
        public_key = public_key.strip()

        # SSH key format: <key_type> <base64_key> [comment]
        parts = public_key.split()

        if len(parts) < 2:
            return (
                False,
                "",
                "Invalid SSH key format. Expected: <key_type> <base64_key> [comment]",
            )

        key_type = parts[0]
        key_data = parts[1]

        # Check if key type is supported
        if key_type not in cls.SUPPORTED_KEY_TYPES:
            return (
                False,
                "",
                f"Unsupported key type: {key_type}. Supported types: {', '.join(cls.SUPPORTED_KEY_TYPES)}",
            )

        # Validate base64 encoding
        try:
            base64.b64decode(key_data)
        except Exception:
            return False, "", "Invalid base64 encoding in key data"

        # Check key length (basic sanity check)
        if len(key_data) < 100:
            return False, "", "Key data too short to be a valid SSH public key"

        return True, key_type, ""

    @classmethod
    def calculate_fingerprint(cls, public_key: str) -> str:
        """
        Calculate SHA256 fingerprint of an SSH public key.

        Args:
            public_key: SSH public key string

        Returns:
            Fingerprint in format: SHA256:xxxxx...
        """
        # Clean the key
        public_key = public_key.strip()
        parts = public_key.split()

        if len(parts) < 2:
            raise ValueError("Invalid SSH key format")

        key_data = parts[1]

        # Decode base64
        try:
            key_bytes = base64.b64decode(key_data)
        except Exception as e:
            raise ValueError(f"Failed to decode key: {e}")

        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(key_bytes)
        fingerprint_bytes = hash_obj.digest()

        # Encode as base64 (without padding)
        fingerprint_b64 = base64.b64encode(fingerprint_bytes).decode().rstrip("=")

        return f"SHA256:{fingerprint_b64}"

    @classmethod
    def extract_comment(cls, public_key: str) -> str:
        """
        Extract comment from SSH public key.

        Args:
            public_key: SSH public key string

        Returns:
            Comment string or empty string if no comment
        """
        parts = public_key.strip().split()
        if len(parts) >= 3:
            return " ".join(parts[2:])
        return ""

    @classmethod
    def format_key(cls, public_key: str) -> str:
        """
        Format SSH public key consistently.

        Args:
            public_key: SSH public key string

        Returns:
            Formatted key string
        """
        parts = public_key.strip().split()
        if len(parts) >= 2:
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]} {' '.join(parts[2:])}"
            return f"{parts[0]} {parts[1]}"
        return public_key.strip()

    @classmethod
    def validate_and_parse(cls, public_key: str) -> dict:
        """
        Validate and parse SSH public key into components.

        Args:
            public_key: SSH public key string

        Returns:
            Dictionary with key information or error

        Example:
            {
                'valid': True,
                'key_type': 'ssh-rsa',
                'fingerprint': 'SHA256:xxx...',
                'comment': 'user@host',
                'formatted_key': 'ssh-rsa AAAA... user@host'
            }
        """
        result = {
            "valid": False,
            "key_type": "",
            "fingerprint": "",
            "comment": "",
            "formatted_key": "",
            "error": "",
        }

        # Validate
        is_valid, key_type, error_msg = cls.validate_public_key(public_key)

        if not is_valid:
            result["error"] = error_msg
            return result

        # Parse
        try:
            result["valid"] = True
            result["key_type"] = key_type
            result["fingerprint"] = cls.calculate_fingerprint(public_key)
            result["comment"] = cls.extract_comment(public_key)
            result["formatted_key"] = cls.format_key(public_key)
        except Exception as e:
            result["valid"] = False
            result["error"] = f"Failed to parse key: {str(e)}"

        return result


# EOF
