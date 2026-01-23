#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - File Operations

This module provides file-related operations for the Gitea REST API.
"""

from typing import Dict, List
from .base import BaseGiteaClient


class FileOperationsMixin:
    """Mixin class for file-related operations"""

    def get_file_contents(
        self, owner: str, repo: str, filepath: str, ref: str = "main"
    ) -> Dict:
        """
        Get file contents from repository

        Args:
            owner: Repository owner
            repo: Repository name
            filepath: Path to file in repository
            ref: Branch/tag/commit (default: main)

        Returns:
            File content object (base64 encoded)
        """
        response = self._request(
            "GET", f"/repos/{owner}/{repo}/contents/{filepath}", params={"ref": ref}
        )
        return response.json()

    def list_files(
        self, owner: str, repo: str, path: str = "", ref: str = "main"
    ) -> List[Dict]:
        """
        List files in repository directory

        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            ref: Branch/tag/commit (default: main)

        Returns:
            List of file/directory objects
        """
        endpoint = f"/repos/{owner}/{repo}/contents"
        if path:
            endpoint += f"/{path}"

        response = self._request("GET", endpoint, params={"ref": ref})
        return response.json()


# EOF
