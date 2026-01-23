#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client for SciTeX Cloud

This module provides a Python wrapper for the Gitea REST API.
Re-exports all components from the modular api_client package for backward compatibility.
"""

from .api_client import (
    BaseGiteaClient,
    convert_git_url_to_https,
    UserOperationsMixin,
    RepositoryOperationsMixin,
    FileOperationsMixin,
    OrganizationOperationsMixin,
    SSHKeyOperationsMixin,
    GiteaClient,
)

__all__ = [
    "BaseGiteaClient",
    "convert_git_url_to_https",
    "UserOperationsMixin",
    "RepositoryOperationsMixin",
    "FileOperationsMixin",
    "OrganizationOperationsMixin",
    "SSHKeyOperationsMixin",
    "GiteaClient",
]

# EOF
