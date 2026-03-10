#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Webhook Operations

This module provides webhook-related operations for the Gitea REST API.
"""

from typing import Dict, List


class WebhookOperationsMixin:
    """Mixin class for webhook-related operations"""

    def list_org_webhooks(self, org: str) -> List[Dict]:
        """
        List webhooks for an organization.

        Args:
            org: Organization name

        Returns:
            List of webhook objects
        """
        response = self._request("GET", f"/orgs/{org}/hooks")
        return response.json()

    def create_org_webhook(
        self,
        org: str,
        url: str,
        events: List[str],
        content_type: str = "json",
        secret: str = "",
        active: bool = True,
    ) -> Dict:
        """
        Create a webhook for an organization.

        Args:
            org: Organization name
            url: Webhook target URL
            events: List of event types to trigger on
            content_type: Payload content type ("json" or "form")
            secret: Webhook secret for signature verification
            active: Whether the webhook is active

        Returns:
            Created webhook object
        """
        data = {
            "type": "gitea",
            "active": active,
            "events": events,
            "config": {
                "url": url,
                "content_type": content_type,
            },
        }
        if secret:
            data["config"]["secret"] = secret

        response = self._request("POST", f"/orgs/{org}/hooks", json=data)
        return response.json()

    def delete_org_webhook(self, org: str, hook_id: int) -> None:
        """
        Delete an organization webhook.

        Args:
            org: Organization name
            hook_id: Webhook ID
        """
        self._request("DELETE", f"/orgs/{org}/hooks/{hook_id}")

    def list_repo_webhooks(self, owner: str, repo: str) -> List[Dict]:
        """
        List webhooks for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of webhook objects
        """
        response = self._request("GET", f"/repos/{owner}/{repo}/hooks")
        return response.json()

    def create_repo_webhook(
        self,
        owner: str,
        repo: str,
        url: str,
        events: List[str],
        content_type: str = "json",
        secret: str = "",
        active: bool = True,
    ) -> Dict:
        """
        Create a webhook for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            url: Webhook target URL
            events: List of event types to trigger on
            content_type: Payload content type ("json" or "form")
            secret: Webhook secret for signature verification
            active: Whether the webhook is active

        Returns:
            Created webhook object
        """
        data = {
            "type": "gitea",
            "active": active,
            "events": events,
            "config": {
                "url": url,
                "content_type": content_type,
            },
        }
        if secret:
            data["config"]["secret"] = secret

        response = self._request("POST", f"/repos/{owner}/{repo}/hooks", json=data)
        return response.json()


# EOF
