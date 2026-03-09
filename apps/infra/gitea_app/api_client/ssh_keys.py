#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - SSH Key Operations

This module provides SSH key-related operations for the Gitea REST API.
"""

from typing import Dict, List
from .base import BaseGiteaClient


class SSHKeyOperationsMixin:
    """Mixin class for SSH key-related operations"""

    def list_ssh_keys(self, username: str = None) -> List[Dict]:
        """
        List SSH keys for a user

        Args:
            username: Username to list keys for (defaults to current user)

        Returns:
            List of SSH key objects
        """
        if username:
            endpoint = f"/users/{username}/keys"
        else:
            endpoint = "/user/keys"

        response = self._request("GET", endpoint)
        return response.json()

    def add_ssh_key(
        self, title: str, key: str, username: str = None, read_only: bool = False
    ) -> Dict:
        """
        Add an SSH key for a user

        Args:
            title: Key title/name
            key: SSH public key content
            username: Username to add key for (requires admin token, defaults to current user)
            read_only: Make key read-only

        Returns:
            Created SSH key object
        """
        data = {"title": title, "key": key.strip(), "read_only": read_only}

        # Use admin endpoint to add key for specific user
        if username:
            endpoint = f"/admin/users/{username}/keys"
        else:
            endpoint = "/user/keys"

        response = self._request("POST", endpoint, json=data)
        return response.json()

    def delete_ssh_key(self, key_id: int, username: str = None) -> bool:
        """
        Delete an SSH key

        Args:
            key_id: SSH key ID
            username: Username to delete key for (requires admin token, defaults to current user)

        Returns:
            True if successful
        """
        # Use admin endpoint to delete key for specific user
        if username:
            endpoint = f"/admin/users/{username}/keys/{key_id}"
        else:
            endpoint = f"/user/keys/{key_id}"

        self._request("DELETE", endpoint)
        return True

    def find_ssh_key_by_fingerprint(
        self, fingerprint: str, username: str = None
    ) -> Dict:
        """
        Find SSH key by fingerprint

        Args:
            fingerprint: SSH key fingerprint (SHA256 format)
            username: Username to search keys for (defaults to current user)

        Returns:
            SSH key object if found, None otherwise
        """
        keys = self.list_ssh_keys(username)

        # Normalize fingerprint format (remove SHA256: prefix if present)
        fingerprint_normalized = fingerprint.replace("SHA256:", "").strip()

        for key in keys:
            key_fingerprint = key.get("fingerprint", "").replace("SHA256:", "").strip()
            if key_fingerprint == fingerprint_normalized:
                return key

        return None


# EOF
