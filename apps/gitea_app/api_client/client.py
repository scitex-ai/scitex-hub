#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Main Client Class

This module provides the main GiteaClient class that combines all operation mixins.
"""

from .base import BaseGiteaClient
from .users import UserOperationsMixin
from .repositories import RepositoryOperationsMixin
from .files import FileOperationsMixin
from .organizations import OrganizationOperationsMixin
from .ssh_keys import SSHKeyOperationsMixin


class GiteaClient(
    BaseGiteaClient,
    UserOperationsMixin,
    RepositoryOperationsMixin,
    FileOperationsMixin,
    OrganizationOperationsMixin,
    SSHKeyOperationsMixin,
):
    """
    Complete Gitea API Client

    This class combines all operation mixins to provide a full-featured
    Gitea REST API client.

    Documentation: https://docs.gitea.io/en-us/api-usage/
    """

    pass


# EOF
