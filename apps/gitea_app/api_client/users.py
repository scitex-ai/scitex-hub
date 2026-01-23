#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - User Operations

This module provides user-related operations for the Gitea REST API.
"""

from typing import Dict
from .base import BaseGiteaClient


class UserOperationsMixin:
    """Mixin class for user-related operations"""

    def get_current_user(self) -> Dict:
        """Get current authenticated user info"""
        response = self._request("GET", "/user")
        return response.json()

    def delete_user(self, username: str) -> bool:
        """
        Delete a Gitea user (requires admin token)

        Args:
            username: Username to delete

        Returns:
            True if successful
        """
        self._request("DELETE", f"/admin/users/{username}")
        return True


# EOF
