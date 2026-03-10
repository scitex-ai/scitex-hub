#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Base Client and Utilities

This module provides the base client class and utility functions
for interacting with the Gitea REST API.
"""

import re
import requests
from typing import Dict
from django.conf import settings
from ..exceptions import GiteaAPIError


def convert_git_url_to_https(git_url: str) -> str:
    """
    Convert Git URL to HTTPS format (required for Gitea migration API)

    Supports:
    - SSH: git@github.com:user/repo.git → https://github.com/user/repo
    - HTTPS: https://github.com/user/repo.git → https://github.com/user/repo
    - HTTPS (no .git): https://github.com/user/repo → https://github.com/user/repo

    Args:
        git_url: Git URL in any format

    Returns:
        HTTPS URL without .git suffix
    """
    git_url = git_url.strip()

    # Pattern 1: SSH format (git@host:user/repo.git)
    ssh_pattern = r"git@([^:]+):(.+?)(?:\.git)?$"
    match = re.match(ssh_pattern, git_url)
    if match:
        host = match.group(1)
        path = match.group(2)
        return f"https://{host}/{path}"

    # Pattern 2: HTTPS format - just remove .git if present
    if git_url.startswith("https://") or git_url.startswith("http://"):
        return git_url.rstrip(".git")

    # If no match, return as-is (might be already correct)
    return git_url


class BaseGiteaClient:
    """
    Base client for interacting with Gitea REST API

    Documentation: https://docs.gitea.io/en-us/api-usage/
    """

    def __init__(self, base_url: str = None, token: str = None):
        """
        Initialize Gitea client

        Args:
            base_url: Gitea instance URL (defaults to settings.GITEA_URL)
            token: API token (defaults to settings.GITEA_TOKEN)
        """
        self.base_url = base_url or settings.GITEA_URL
        self.api_url = f"{self.base_url}/api/v1"
        self.token = token or settings.GITEA_TOKEN

        if not self.token:
            raise GiteaAPIError("Gitea API token not configured")

    def _get_headers(self, extra_headers: Dict = None) -> Dict:
        """Build request headers with authentication"""
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to Gitea API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/user/repos')
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            GiteaAPIError: If request fails
        """
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers(kwargs.pop("headers", None))

        try:
            response = requests.request(
                method=method, url=url, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.HTTPError:
            # Parse error message from Gitea response
            error_msg = f"Gitea API error ({response.status_code})"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
            except (ValueError, requests.RequestException):
                # JSON parsing failed, use response text instead
                if response.text:
                    error_msg = response.text[:200]

            raise GiteaAPIError(error_msg)
        except requests.RequestException as e:
            raise GiteaAPIError(f"Request failed: {e}")


# EOF
