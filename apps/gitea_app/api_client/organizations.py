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

    def list_org_members(self, org: str) -> List[Dict]:
        """
        List members of an organization.

        Args:
            org: Organization name

        Returns:
            List of user objects
        """
        response = self._request("GET", f"/orgs/{org}/members")
        return response.json()

    def add_org_member(self, org: str, username: str, role: str = "member") -> None:
        """
        Add a user to an organization (via Owners team or direct invite).

        Gitea's org member API works through teams. This method adds the user
        to the org's default team or creates a membership invite if supported.

        Args:
            org: Organization name
            username: Username to add
            role: Role in the org ("owner" or "member")
        """
        # Gitea adds org members via team membership. Use admin API to directly set.
        self._request("PUT", f"/orgs/{org}/members/{username}")

    def remove_org_member(self, org: str, username: str) -> None:
        """
        Remove a user from an organization.

        Args:
            org: Organization name
            username: Username to remove
        """
        self._request("DELETE", f"/orgs/{org}/members/{username}")

    def is_org_member(self, org: str, username: str) -> bool:
        """
        Check if a user is a member of an organization.

        Args:
            org: Organization name
            username: Username to check

        Returns:
            True if user is a member
        """
        from ..exceptions import GiteaAPIError

        try:
            self._request("GET", f"/orgs/{org}/members/{username}")
            return True
        except GiteaAPIError:
            return False


# EOF
