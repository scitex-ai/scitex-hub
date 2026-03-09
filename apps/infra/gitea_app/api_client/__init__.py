#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Modular Structure

This package provides a modular structure for the Gitea REST API client.
All components are re-exported here for backward compatibility.
"""

from ..exceptions import GiteaAPIError
from .base import BaseGiteaClient, convert_git_url_to_https
from .client import GiteaClient
from .files import FileOperationsMixin
from .organizations import OrganizationOperationsMixin
from .pull_requests import PullRequestOperationsMixin
from .repositories import RepositoryOperationsMixin
from .ssh_keys import SSHKeyOperationsMixin
from .users import UserOperationsMixin
from .webhooks import WebhookOperationsMixin

__all__ = [
    "BaseGiteaClient",
    "convert_git_url_to_https",
    "UserOperationsMixin",
    "RepositoryOperationsMixin",
    "FileOperationsMixin",
    "OrganizationOperationsMixin",
    "SSHKeyOperationsMixin",
    "PullRequestOperationsMixin",
    "WebhookOperationsMixin",
    "GiteaClient",
    "GiteaAPIError",
]

# EOF
