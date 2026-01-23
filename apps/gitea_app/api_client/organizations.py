#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Organization Operations

This module provides organization-related operations for the Gitea REST API.
"""

from typing import Dict, List
from .base import BaseGiteaClient


class OrganizationOperationsMixin:
    """Mixin class for organization-related operations"""

    def create_organization(
        self,
        name: str,
        full_name: str = "",
        description: str = "",
        website: str = "",
        location: str = "",
    ) -> Dict:
        """
        Create an organization

        Args:
            name: Organization username
            full_name: Full organization name
            description: Description
            website: Website URL
            location: Location

        Returns:
            Created organization object
        """
        data = {
            "username": name,
            "full_name": full_name or name,
            "description": description,
            "website": website,
            "location": location,
        }

        response = self._request("POST", "/orgs", json=data)
        return response.json()

    def list_organizations(self) -> List[Dict]:
        """List organizations for current user"""
        response = self._request("GET", "/user/orgs")
        return response.json()


# EOF
