#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - File Operations

This module provides file-related operations for the Gitea REST API.
"""

from typing import Dict, List

from .base import path_segment, repo_path


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
            "GET", f"/repos/{path_segment(owner)}/{path_segment(repo)}/contents/{repo_path(filepath)}", params={"ref": ref}
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
        endpoint = f"/repos/{path_segment(owner)}/{path_segment(repo)}/contents"
        if path:
            endpoint += f"/{repo_path(path)}"

        response = self._request("GET", endpoint, params={"ref": ref})
        return response.json()

    def create_file(
        self,
        owner: str,
        repo: str,
        filepath: str,
        content: str,
        message: str = "",
        branch: str = "main",
    ) -> Dict:
        """
        Create a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            filepath: Path for the new file
            content: File content (will be base64-encoded automatically by Gitea)
            message: Commit message
            branch: Target branch

        Returns:
            File response object
        """
        import base64

        data = {
            "content": base64.b64encode(content.encode()).decode(),
            "message": message or f"Create {filepath}",
            "branch": branch,
        }
        response = self._request(
            "POST", f"/repos/{path_segment(owner)}/{path_segment(repo)}/contents/{repo_path(filepath)}", json=data
        )
        return response.json()

    def update_file(
        self,
        owner: str,
        repo: str,
        filepath: str,
        content: str,
        sha: str,
        message: str = "",
        branch: str = "main",
    ) -> Dict:
        """
        Update an existing file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            filepath: Path to the file
            content: New file content
            sha: SHA of the file being replaced (from get_file_contents)
            message: Commit message
            branch: Target branch

        Returns:
            File response object
        """
        import base64

        data = {
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha,
            "message": message or f"Update {filepath}",
            "branch": branch,
        }
        response = self._request(
            "PUT", f"/repos/{path_segment(owner)}/{path_segment(repo)}/contents/{repo_path(filepath)}", json=data
        )
        return response.json()


# EOF
