#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Modular Structure

This package provides a modular structure for the Gitea REST API client.
All components are re-exported here for backward compatibility.
"""

from .base import BaseGiteaClient, convert_git_url_to_https
from .users import UserOperationsMixin
from .repositories import RepositoryOperationsMixin
from .files import FileOperationsMixin
from .organizations import OrganizationOperationsMixin
from .ssh_keys import SSHKeyOperationsMixin
from .client import GiteaClient
from ..exceptions import GiteaAPIError

__all__ = [
    "BaseGiteaClient",
    "convert_git_url_to_https",
    "UserOperationsMixin",
    "RepositoryOperationsMixin",
    "FileOperationsMixin",
    "OrganizationOperationsMixin",
    "SSHKeyOperationsMixin",
    "GiteaClient",
    "GiteaAPIError",
]

# EOF
