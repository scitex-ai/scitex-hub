#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/organizations.py"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.gitea_app.api_client.client import GiteaClient
from apps.gitea_app.exceptions import GiteaAPIError

BASE_URL = "http://gitea:3000"
TOKEN = "test-token"
API_URL = f"{BASE_URL}/api/v1"


@pytest.fixture(autouse=True)
def gitea_settings(settings):
    settings.GITEA_URL = BASE_URL
    settings.GITEA_TOKEN = TOKEN


@pytest.fixture
def mock_response():
    """Create a mock response that passes raise_for_status."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def client():
    return GiteaClient(base_url=BASE_URL, token=TOKEN)


class TestCreateOrganization:
    """Tests for OrganizationOperationsMixin.create_organization"""

    @patch("requests.request")
    def test_create_organization_minimal(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"username": "my-org", "id": 1}
        mock_request.return_value = mock_response

        result = client.create_organization("my-org")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs"

        payload = call_kwargs.kwargs["json"]
        assert payload["username"] == "my-org"
        assert payload["full_name"] == "my-org"
        assert payload["description"] == ""
        assert payload["website"] == ""
        assert payload["location"] == ""
        assert result["username"] == "my-org"

    @patch("requests.request")
    def test_create_organization_full_params(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"username": "sci-lab", "id": 2}
        mock_request.return_value = mock_response

        result = client.create_organization(
            "sci-lab",
            full_name="Science Lab",
            description="Research org",
            website="https://sci-lab.org",
            location="Tokyo",
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["username"] == "sci-lab"
        assert payload["full_name"] == "Science Lab"
        assert payload["description"] == "Research org"
        assert payload["website"] == "https://sci-lab.org"
        assert payload["location"] == "Tokyo"
        assert result["id"] == 2

    @patch("requests.request")
    def test_create_organization_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 422
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "org already exists"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="org already exists"):
            client.create_organization("existing-org")


class TestListOrganizations:
    """Tests for OrganizationOperationsMixin.list_organizations"""

    @patch("requests.request")
    def test_list_organizations(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"username": "org1", "id": 1},
            {"username": "org2", "id": 2},
        ]
        mock_request.return_value = mock_response

        result = client.list_organizations()

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/user/orgs"
        assert len(result) == 2
        assert result[0]["username"] == "org1"

    @patch("requests.request")
    def test_list_organizations_empty(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = client.list_organizations()

        assert result == []

    @patch("requests.request")
    def test_list_organizations_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 401
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "unauthorized"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="unauthorized"):
            client.list_organizations()


class TestGetOrganization:
    """Tests for OrganizationOperationsMixin.get_organization"""

    @patch("requests.request")
    def test_get_organization(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "username": "my-org",
            "id": 5,
            "full_name": "My Organization",
        }
        mock_request.return_value = mock_response

        result = client.get_organization("my-org")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org"
        assert result["username"] == "my-org"
        assert result["full_name"] == "My Organization"

    @patch("requests.request")
    def test_get_organization_not_found(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "organization not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="organization not found"):
            client.get_organization("nonexistent")


class TestListOrgRepos:
    """Tests for OrganizationOperationsMixin.list_org_repos"""

    @patch("requests.request")
    def test_list_org_repos(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"name": "repo-a", "full_name": "my-org/repo-a"},
            {"name": "repo-b", "full_name": "my-org/repo-b"},
        ]
        mock_request.return_value = mock_response

        result = client.list_org_repos("my-org")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org/repos"
        assert len(result) == 2
        assert result[0]["name"] == "repo-a"

    @patch("requests.request")
    def test_list_org_repos_empty(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = client.list_org_repos("empty-org")

        assert result == []


class TestListOrgTeams:
    """Tests for OrganizationOperationsMixin.list_org_teams"""

    @patch("requests.request")
    def test_list_org_teams(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"id": 1, "name": "Owners"},
            {"id": 2, "name": "Developers"},
        ]
        mock_request.return_value = mock_response

        result = client.list_org_teams("my-org")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org/teams"
        assert len(result) == 2
        assert result[1]["name"] == "Developers"

    @patch("requests.request")
    def test_list_org_teams_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 403
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "forbidden"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="forbidden"):
            client.list_org_teams("restricted-org")


class TestAddTeamMember:
    """Tests for OrganizationOperationsMixin.add_team_member"""

    @patch("requests.request")
    def test_add_team_member(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        client.add_team_member(42, "new-user")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "PUT"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/teams/42/members/new-user"

    @patch("requests.request")
    def test_add_team_member_returns_none(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        result = client.add_team_member(1, "user1")

        assert result is None

    @patch("requests.request")
    def test_add_team_member_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "team not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="team not found"):
            client.add_team_member(999, "user1")


class TestCreateOrgRepository:
    """Tests for OrganizationOperationsMixin.create_org_repository"""

    @patch("requests.request")
    def test_create_org_repository_minimal(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "name": "new-repo",
            "full_name": "my-org/new-repo",
            "id": 10,
        }
        mock_request.return_value = mock_response

        result = client.create_org_repository("my-org", "new-repo")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org/repos"

        payload = call_kwargs.kwargs["json"]
        assert payload["name"] == "new-repo"
        assert payload["description"] == ""
        assert payload["private"] is False
        assert payload["auto_init"] is True
        assert result["full_name"] == "my-org/new-repo"

    @patch("requests.request")
    def test_create_org_repository_full_params(
        self, mock_request, client, mock_response
    ):
        mock_response.json.return_value = {"name": "private-repo", "id": 11}
        mock_request.return_value = mock_response

        result = client.create_org_repository(
            "my-org",
            "private-repo",
            description="A private repository",
            private=True,
            auto_init=False,
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["name"] == "private-repo"
        assert payload["description"] == "A private repository"
        assert payload["private"] is True
        assert payload["auto_init"] is False

    @patch("requests.request")
    def test_create_org_repository_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 409
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "repository already exists"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="repository already exists"):
            client.create_org_repository("my-org", "existing-repo")


if __name__ == "__main__":
    pytest.main([__file__])
