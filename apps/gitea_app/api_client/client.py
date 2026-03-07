#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Main Client Class

This module provides the main GiteaClient class that combines all operation mixins.
"""

from .base import BaseGiteaClient
from .files import FileOperationsMixin
from .organizations import OrganizationOperationsMixin
from .pull_requests import PullRequestOperationsMixin
from .repositories import RepositoryOperationsMixin
from .ssh_keys import SSHKeyOperationsMixin
from .users import UserOperationsMixin
from .webhooks import WebhookOperationsMixin


class GiteaClient(
    BaseGiteaClient,
    UserOperationsMixin,
    RepositoryOperationsMixin,
    FileOperationsMixin,
    OrganizationOperationsMixin,
    SSHKeyOperationsMixin,
    PullRequestOperationsMixin,
    WebhookOperationsMixin,
):
    """
    Complete Gitea API Client

    This class combines all operation mixins to provide a full-featured
    Gitea REST API client.

    Documentation: https://docs.gitea.io/en-us/api-usage/
    """

    pass


# EOF
