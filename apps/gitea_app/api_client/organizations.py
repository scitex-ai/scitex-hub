#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea API Client - Organization Operations

This module provides organization-related operations for the Gitea REST API.
"""

from typing import Dict, List


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

    def get_organization(self, org: str) -> Dict:
        """
        Get organization details.

        Args:
            org: Organization name

        Returns:
            Organization object
        """
        response = self._request("GET", f"/orgs/{org}")
        return response.json()

    def list_org_repos(self, org: str) -> List[Dict]:
        """
        List repositories owned by an organization.

        Args:
            org: Organization name

        Returns:
            List of repository objects
        """
        response = self._request("GET", f"/orgs/{org}/repos")
        return response.json()

    def list_org_teams(self, org: str) -> List[Dict]:
        """
        List teams in an organization.

        Args:
            org: Organization name

        Returns:
            List of team objects
        """
        response = self._request("GET", f"/orgs/{org}/teams")
        return response.json()

    def add_team_member(self, team_id: int, username: str) -> None:
        """
        Add a user to an organization team.

        Args:
            team_id: Team ID
            username: Username to add
        """
        self._request("PUT", f"/teams/{team_id}/members/{username}")

    def create_org_repository(
        self,
        org: str,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
    ) -> Dict:
        """
        Create a repository under an organization.

        Args:
            org: Organization name
            name: Repository name
            description: Repository description
            private: Make repository private
            auto_init: Initialize with README

        Returns:
            Created repository object
        """
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        response = self._request("POST", f"/orgs/{org}/repos", json=data)
        return response.json()


# EOF
