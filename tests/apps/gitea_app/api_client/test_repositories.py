#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/repositories.py"""

from unittest.mock import MagicMock, patch

import pytest
import requests as req

from apps.infra.gitea_app.api_client.client import GiteaClient
from apps.infra.gitea_app.exceptions import GiteaAPIError

BASE_API = "http://gitea:3000/api/v1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def gitea_settings(settings):
    settings.GITEA_URL = "http://gitea:3000"
    settings.GITEA_TOKEN = "test-token"


@pytest.fixture
def client():
    return GiteaClient(base_url="http://gitea:3000", token="test-token")


def _mock_ok(json_data=None):
    """Create a mock response that passes raise_for_status."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _mock_error(status_code, message):
    """Create a mock response that triggers HTTPError."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.side_effect = req.HTTPError()
    resp.json.return_value = {"message": message}
    return resp


# ---------------------------------------------------------------------------
# list_repositories
# ---------------------------------------------------------------------------


class TestListRepositories:
    """Tests for RepositoryOperationsMixin.list_repositories."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_lists_current_user_repos_when_no_username(self, mock_request, client):
        repos = [{"name": "repo1"}, {"name": "repo2"}]
        mock_request.return_value = _mock_ok(repos)

        result = client.list_repositories()

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "GET"
        assert kw["url"] == f"{BASE_API}/user/repos"
        assert result == repos

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_lists_specific_user_repos(self, mock_request, client):
        repos = [{"name": "their-repo"}]
        mock_request.return_value = _mock_ok(repos)

        result = client.list_repositories(username="otheruser")

        kw = mock_request.call_args.kwargs
        assert kw["url"] == f"{BASE_API}/users/otheruser/repos"
        assert result == repos


# ---------------------------------------------------------------------------
# create_repository
# ---------------------------------------------------------------------------


class TestCreateRepository:
    """Tests for RepositoryOperationsMixin.create_repository."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_creates_repo_for_current_user(self, mock_request, client):
        created = {"name": "my-repo", "id": 10}
        mock_request.return_value = _mock_ok(created)

        result = client.create_repository("my-repo")

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "POST"
        assert kw["url"] == f"{BASE_API}/user/repos"
        payload = kw["json"]
        assert payload["name"] == "my-repo"
        assert payload["auto_init"] is True
        assert result == created

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_creates_repo_for_specific_owner(self, mock_request, client):
        created = {"name": "team-repo", "id": 11}
        mock_request.return_value = _mock_ok(created)

        result = client.create_repository("team-repo", owner="orguser")

        kw = mock_request.call_args.kwargs
        assert kw["url"] == f"{BASE_API}/admin/users/orguser/repos"
        assert result == created

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_includes_optional_fields(self, mock_request, client):
        mock_request.return_value = _mock_ok({"name": "r"})

        client.create_repository(
            "r",
            description="desc",
            private=True,
            gitignores="Python",
            license="MIT",
            readme="Default",
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["description"] == "desc"
        assert payload["private"] is True
        assert payload["gitignores"] == "Python"
        assert payload["license"] == "MIT"
        assert payload["readme"] == "Default"


# ---------------------------------------------------------------------------
# get_repository
# ---------------------------------------------------------------------------


class TestGetRepository:
    """Tests for RepositoryOperationsMixin.get_repository."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_gets_repo_by_owner_and_name(self, mock_request, client):
        repo = {"full_name": "alice/project", "id": 5}
        mock_request.return_value = _mock_ok(repo)

        result = client.get_repository("alice", "project")

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "GET"
        assert kw["url"] == f"{BASE_API}/repos/alice/project"
        assert result == repo

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_propagates_not_found_error(self, mock_request, client):
        mock_request.return_value = _mock_error(404, "repo not found")

        with pytest.raises(GiteaAPIError, match="repo not found"):
            client.get_repository("alice", "missing")


# ---------------------------------------------------------------------------
# delete_repository
# ---------------------------------------------------------------------------


class TestDeleteRepository:
    """Tests for RepositoryOperationsMixin.delete_repository."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_sends_delete_request(self, mock_request, client):
        mock_request.return_value = _mock_ok()

        result = client.delete_repository("alice", "old-repo")

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "DELETE"
        assert kw["url"] == f"{BASE_API}/repos/alice/old-repo"
        assert result is True


# ---------------------------------------------------------------------------
# fork_repository
# ---------------------------------------------------------------------------


class TestForkRepository:
    """Tests for RepositoryOperationsMixin.fork_repository."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_forks_repo(self, mock_request, client):
        forked = {"name": "upstream-repo", "fork": True}
        mock_request.return_value = _mock_ok(forked)

        result = client.fork_repository("upstream", "upstream-repo")

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "POST"
        assert kw["url"] == f"{BASE_API}/repos/upstream/upstream-repo/forks"
        assert kw["json"] == {}
        assert result == forked

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_forks_repo_to_organization(self, mock_request, client):
        forked = {"name": "upstream-repo", "fork": True}
        mock_request.return_value = _mock_ok(forked)

        client.fork_repository("upstream", "upstream-repo", organization="myorg")

        kw = mock_request.call_args.kwargs
        assert kw["json"] == {"organization": "myorg"}


# ---------------------------------------------------------------------------
# update_repository
# ---------------------------------------------------------------------------


class TestUpdateRepository:
    """Tests for RepositoryOperationsMixin.update_repository."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_patches_repo_with_kwargs(self, mock_request, client):
        updated = {"name": "project", "private": True}
        mock_request.return_value = _mock_ok(updated)

        result = client.update_repository("alice", "project", private=True)

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "PATCH"
        assert kw["url"] == f"{BASE_API}/repos/alice/project"
        assert kw["json"] == {"private": True}
        assert result == updated


# ---------------------------------------------------------------------------
# get_branch
# ---------------------------------------------------------------------------


class TestGetBranch:
    """Tests for RepositoryOperationsMixin.get_branch."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_gets_branch_info(self, mock_request, client):
        branch = {"name": "main", "commit": {"id": "abc123"}}
        mock_request.return_value = _mock_ok(branch)

        result = client.get_branch("alice", "project", "main")

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "GET"
        assert kw["url"] == f"{BASE_API}/repos/alice/project/branches/main"
        assert result == branch


# ---------------------------------------------------------------------------
# list_commits
# ---------------------------------------------------------------------------


class TestListCommits:
    """Tests for RepositoryOperationsMixin.list_commits."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_lists_commits_with_default_params(self, mock_request, client):
        commits = [{"sha": "aaa"}, {"sha": "bbb"}]
        mock_request.return_value = _mock_ok(commits)

        result = client.list_commits("alice", "project")

        kw = mock_request.call_args.kwargs
        assert kw["method"] == "GET"
        assert kw["url"] == f"{BASE_API}/repos/alice/project/git/commits"
        assert kw["params"] == {"limit": 10}
        assert result == commits

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_passes_sha_and_limit_params(self, mock_request, client):
        mock_request.return_value = _mock_ok([])

        client.list_commits("alice", "project", sha="develop", limit=5)

        kw = mock_request.call_args.kwargs
        assert kw["params"] == {"limit": 5, "sha": "develop"}


# ---------------------------------------------------------------------------
# check_collaborator
# ---------------------------------------------------------------------------


class TestCheckCollaborator:
    """Tests for RepositoryOperationsMixin.check_collaborator."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_returns_true_when_collaborator(self, mock_request, client):
        mock_request.return_value = _mock_ok()

        assert client.check_collaborator("alice", "project", "bob") is True

        kw = mock_request.call_args.kwargs
        assert kw["url"] == f"{BASE_API}/repos/alice/project/collaborators/bob"

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_returns_false_when_not_collaborator(self, mock_request, client):
        mock_request.return_value = _mock_error(404, "not a collaborator")

        assert client.check_collaborator("alice", "project", "stranger") is False


if __name__ == "__main__":
    pytest.main([__file__])
