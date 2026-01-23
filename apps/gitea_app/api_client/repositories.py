#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Repository Operations

This module provides repository-related operations for the Gitea REST API.
"""

from typing import Dict, List
from .base import BaseGiteaClient, convert_git_url_to_https


class RepositoryOperationsMixin:
    """Mixin class for repository-related operations"""

    def list_repositories(self, username: str = None) -> List[Dict]:
        """
        List repositories

        Args:
            username: Username to list repos for (defaults to current user)

        Returns:
            List of repository objects
        """
        if username:
            endpoint = f"/users/{username}/repos"
        else:
            endpoint = "/user/repos"

        response = self._request("GET", endpoint)
        return response.json()

    def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
        gitignores: str = "",
        license: str = "",
        readme: str = "Default",
        owner: str = None,
    ) -> Dict:
        """
        Create a new repository

        Args:
            name: Repository name
            description: Repository description
            private: Make repository private
            auto_init: Initialize with README
            gitignores: Gitignore template (e.g., 'Python')
            license: License template (e.g., 'MIT')
            readme: README template (e.g., 'Default')
            owner: Username to create repo for (requires admin token, defaults to authenticated user)

        Returns:
            Created repository object
        """
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }

        if gitignores:
            data["gitignores"] = gitignores
        if license:
            data["license"] = license
        if readme:
            data["readme"] = readme

        # Use admin endpoint to create repo for specific user
        if owner:
            endpoint = f"/admin/users/{owner}/repos"
        else:
            endpoint = "/user/repos"

        response = self._request("POST", endpoint, json=data)
        return response.json()

    def get_repository(self, owner: str, repo: str) -> Dict:
        """
        Get repository information

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository object
        """
        response = self._request("GET", f"/repos/{owner}/{repo}")
        return response.json()

    def delete_repository(self, owner: str, repo: str) -> bool:
        """
        Delete a repository

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            True if successful
        """
        self._request("DELETE", f"/repos/{owner}/{repo}")
        return True

    def migrate_repository(
        self,
        clone_addr: str,
        repo_name: str = None,
        service: str = "github",
        auth_token: str = "",
        mirror: bool = False,
        private: bool = False,
        description: str = "",
        wiki: bool = True,
        milestones: bool = True,
        labels: bool = True,
        issues: bool = True,
        pull_requests: bool = True,
        releases: bool = True,
    ) -> Dict:
        """
        Migrate/import repository from external source

        Args:
            clone_addr: Git clone URL (HTTPS or SSH format)
            repo_name: Name for imported repo (extracted from URL if not provided)
            service: Source service ('github', 'gitlab', 'gitea', 'gogs')
            auth_token: Authentication token for private repos
            mirror: Create as mirror (keep synced)
            private: Make repository private
            description: Repository description
            wiki: Import wiki
            milestones: Import milestones
            labels: Import labels
            issues: Import issues
            pull_requests: Import pull requests
            releases: Import releases

        Returns:
            Created repository object
        """
        # Convert SSH URLs to HTTPS (Gitea API requires HTTPS)
        clone_addr = convert_git_url_to_https(clone_addr)

        # Extract repo name from URL if not provided
        # Preserves original name from the source repository
        if not repo_name:
            repo_name = clone_addr.rstrip("/").split("/")[-1]
            # Remove .git suffix while preserving case and other characters
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

        data = {
            "clone_addr": clone_addr,
            "service": service,
            "repo_name": repo_name,
            "mirror": mirror,
            "private": private,
            "description": description or f"Imported from {clone_addr}",
            "wiki": wiki,
            "milestones": milestones,
            "labels": labels,
            "issues": issues,
            "pull_requests": pull_requests,
            "releases": releases,
        }

        if auth_token:
            data["auth_token"] = auth_token

        response = self._request("POST", "/repos/migrate", json=data)
        return response.json()

    def fork_repository(self, owner: str, repo: str, organization: str = None) -> Dict:
        """
        Fork a repository

        Args:
            owner: Original repository owner
            repo: Original repository name
            organization: Organization to fork to (optional)

        Returns:
            Forked repository object
        """
        data = {}
        if organization:
            data["organization"] = organization

        response = self._request("POST", f"/repos/{owner}/{repo}/forks", json=data)
        return response.json()


# EOF
