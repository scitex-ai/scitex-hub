#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-28 (ywatanabe)"
# File: ./apps/gitea_app/exceptions.py

"""
Custom exceptions for Gitea integration
"""


class GiteaAPIError(Exception):
    """Base exception for Gitea API errors"""

    pass


class GiteaUserCreationError(GiteaAPIError):
    """Exception raised when Gitea user creation fails"""

    def __init__(self, username: str, reason: str):
        self.username = username
        self.reason = reason
        super().__init__(f"Failed to create Gitea user '{username}': {reason}")


class GiteaRepositoryCreationError(GiteaAPIError):
    """Exception raised when Gitea repository creation fails"""

    def __init__(self, repo_name: str, reason: str):
        self.repo_name = repo_name
        self.reason = reason
        super().__init__(f"Failed to create Gitea repository '{repo_name}': {reason}")


class GiteaConnectionError(GiteaAPIError):
    """Exception raised when cannot connect to Gitea server"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Cannot connect to Gitea server: {reason}")


# EOF
