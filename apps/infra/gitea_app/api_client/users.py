#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - User Operations

This module provides user-related operations for the Gitea REST API.
"""

from typing import Dict


class UserOperationsMixin:
    """Mixin class for user-related operations"""

    def get_current_user(self) -> Dict:
        """Get current authenticated user info"""
        response = self._request("GET", "/user")
        return response.json()

    def get_user(self, username: str) -> Dict:
        """
        Get a user by username.

        Args:
            username: Username to look up

        Returns:
            User object
        """
        response = self._request("GET", f"/users/{username}")
        return response.json()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        must_change_password: bool = False,
    ) -> Dict:
        """
        Create a new user (requires admin token).

        Args:
            username: Username
            email: Email address
            password: Initial password
            must_change_password: Force password change on first login

        Returns:
            Created user object
        """
        data = {
            "username": username,
            "email": email,
            "password": password,
            "must_change_password": must_change_password,
        }
        response = self._request("POST", "/admin/users", json=data)
        return response.json()

    def user_exists(self, username: str) -> bool:
        """
        Check if a user exists.

        Args:
            username: Username to check

        Returns:
            True if user exists, False otherwise
        """
        from ..exceptions import GiteaAPIError

        try:
            self._request("GET", f"/users/{username}")
            return True
        except GiteaAPIError:
            return False

    def delete_user(self, username: str) -> bool:
        """
        Delete a Gitea user (requires admin token).

        Args:
            username: Username to delete

        Returns:
            True if successful
        """
        self._request("DELETE", f"/admin/users/{username}")
        return True


# EOF
