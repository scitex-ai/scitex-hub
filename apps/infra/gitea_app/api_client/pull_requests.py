#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Pull Request Operations

This module provides pull-request-related operations for the Gitea REST API.
"""

from typing import Dict, List

from .base import path_segment


class PullRequestOperationsMixin:
    """Mixin class for pull-request-related operations"""

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        head: str = "main",
        base: str = "main",
    ) -> Dict:
        """
        Create a pull request.

        For cross-repo PRs (forks), use head="fork_owner:branch".

        Args:
            owner: Repository owner (target repo)
            repo: Repository name (target repo)
            title: PR title
            body: PR description
            head: Source branch (or "owner:branch" for cross-repo)
            base: Target branch

        Returns:
            Created pull request object
        """
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }
        response = self._request("POST", f"/repos/{path_segment(owner)}/{path_segment(repo)}/pulls", json=data)
        return response.json()

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict:
        """
        Get a pull request by number.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            Pull request object
        """
        response = self._request("GET", f"/repos/{path_segment(owner)}/{path_segment(repo)}/pulls/{path_segment(pr_number)}")
        return response.json()

    def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
    ) -> List[Dict]:
        """
        List pull requests on a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Filter by state ("open", "closed", "all")

        Returns:
            List of pull request objects
        """
        response = self._request(
            "GET",
            f"/repos/{path_segment(owner)}/{path_segment(repo)}/pulls",
            params={"state": state},
        )
        return response.json()

    def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        method: str = "merge",
    ) -> None:
        """
        Merge a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            method: Merge method ("merge", "rebase", "squash")
        """
        self._request(
            "POST",
            f"/repos/{path_segment(owner)}/{path_segment(repo)}/pulls/{path_segment(pr_number)}/merge",
            json={"Do": method},
        )

    def close_pull_request(self, owner: str, repo: str, pr_number: int) -> None:
        """
        Close a pull request without merging.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
        """
        self._request(
            "PATCH",
            f"/repos/{path_segment(owner)}/{path_segment(repo)}/pulls/{path_segment(pr_number)}",
            json={"state": "closed"},
        )

    def comment_on_issue(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> Dict:
        """
        Add a comment on an issue or pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue/PR number
            body: Comment body (markdown)

        Returns:
            Created comment object
        """
        response = self._request(
            "POST",
            f"/repos/{path_segment(owner)}/{path_segment(repo)}/issues/{path_segment(issue_number)}/comments",
            json={"body": body},
        )
        return response.json()


# EOF
