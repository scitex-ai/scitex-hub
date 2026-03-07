#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/pull_requests.py"""

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


class TestCreatePullRequest:
    """Tests for PullRequestOperationsMixin.create_pull_request"""

    @patch("requests.request")
    def test_create_pull_request_basic(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "id": 1,
            "number": 1,
            "title": "Fix bug",
            "state": "open",
        }
        mock_request.return_value = mock_response

        result = client.create_pull_request(
            "owner1",
            "repo1",
            "Fix bug",
            body="Fixes issue #42",
            head="feature",
            base="main",
        )

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/pulls"

        payload = call_kwargs.kwargs["json"]
        assert payload["title"] == "Fix bug"
        assert payload["body"] == "Fixes issue #42"
        assert payload["head"] == "feature"
        assert payload["base"] == "main"
        assert result["number"] == 1

    @patch("requests.request")
    def test_create_pull_request_defaults(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 2, "number": 2, "title": "PR"}
        mock_request.return_value = mock_response

        client.create_pull_request("owner1", "repo1", "PR")

        payload = mock_request.call_args.kwargs["json"]
        assert payload["body"] == ""
        assert payload["head"] == "main"
        assert payload["base"] == "main"

    @patch("requests.request")
    def test_create_pull_request_cross_repo(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 3, "number": 3}
        mock_request.return_value = mock_response

        client.create_pull_request(
            "upstream", "repo1", "From fork", head="fork-owner:feature", base="main"
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["head"] == "fork-owner:feature"

    @patch("requests.request")
    def test_create_pull_request_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 422
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "head branch does not exist"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="head branch does not exist"):
            client.create_pull_request("owner1", "repo1", "Bad PR", head="nonexistent")


class TestGetPullRequest:
    """Tests for PullRequestOperationsMixin.get_pull_request"""

    @patch("requests.request")
    def test_get_pull_request(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "id": 1,
            "number": 7,
            "title": "Add feature",
            "state": "open",
            "merged": False,
        }
        mock_request.return_value = mock_response

        result = client.get_pull_request("owner1", "repo1", 7)

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/pulls/7"
        assert result["number"] == 7
        assert result["title"] == "Add feature"

    @patch("requests.request")
    def test_get_pull_request_not_found(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "pull request not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="pull request not found"):
            client.get_pull_request("owner1", "repo1", 999)


class TestListPullRequests:
    """Tests for PullRequestOperationsMixin.list_pull_requests"""

    @patch("requests.request")
    def test_list_pull_requests_default_state(
        self, mock_request, client, mock_response
    ):
        mock_response.json.return_value = [
            {"number": 1, "title": "PR 1", "state": "open"},
            {"number": 2, "title": "PR 2", "state": "open"},
        ]
        mock_request.return_value = mock_response

        result = client.list_pull_requests("owner1", "repo1")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/pulls"
        assert call_kwargs.kwargs["params"] == {"state": "open"}
        assert len(result) == 2

    @patch("requests.request")
    def test_list_pull_requests_closed_state(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"number": 3, "state": "closed"},
        ]
        mock_request.return_value = mock_response

        result = client.list_pull_requests("owner1", "repo1", state="closed")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["params"] == {"state": "closed"}
        assert len(result) == 1

    @patch("requests.request")
    def test_list_pull_requests_all_state(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client.list_pull_requests("owner1", "repo1", state="all")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["params"] == {"state": "all"}

    @patch("requests.request")
    def test_list_pull_requests_empty(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = client.list_pull_requests("owner1", "repo1")

        assert result == []


class TestMergePullRequest:
    """Tests for PullRequestOperationsMixin.merge_pull_request"""

    @patch("requests.request")
    def test_merge_pull_request_default_method(
        self, mock_request, client, mock_response
    ):
        mock_request.return_value = mock_response

        client.merge_pull_request("owner1", "repo1", 5)

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert (
            call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/pulls/5/merge"
        )
        assert call_kwargs.kwargs["json"] == {"Do": "merge"}

    @patch("requests.request")
    def test_merge_pull_request_squash(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        client.merge_pull_request("owner1", "repo1", 5, method="squash")

        payload = mock_request.call_args.kwargs["json"]
        assert payload["Do"] == "squash"

    @patch("requests.request")
    def test_merge_pull_request_rebase(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        client.merge_pull_request("owner1", "repo1", 5, method="rebase")

        payload = mock_request.call_args.kwargs["json"]
        assert payload["Do"] == "rebase"

    @patch("requests.request")
    def test_merge_pull_request_returns_none(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        result = client.merge_pull_request("owner1", "repo1", 5)

        assert result is None

    @patch("requests.request")
    def test_merge_pull_request_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 405
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "merge conflict"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="merge conflict"):
            client.merge_pull_request("owner1", "repo1", 5)


class TestClosePullRequest:
    """Tests for PullRequestOperationsMixin.close_pull_request"""

    @patch("requests.request")
    def test_close_pull_request(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        client.close_pull_request("owner1", "repo1", 3)

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "PATCH"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/pulls/3"
        assert call_kwargs.kwargs["json"] == {"state": "closed"}

    @patch("requests.request")
    def test_close_pull_request_returns_none(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        result = client.close_pull_request("owner1", "repo1", 3)

        assert result is None

    @patch("requests.request")
    def test_close_pull_request_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "pull request not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="pull request not found"):
            client.close_pull_request("owner1", "repo1", 999)


class TestCommentOnIssue:
    """Tests for PullRequestOperationsMixin.comment_on_issue"""

    @patch("requests.request")
    def test_comment_on_issue(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "id": 100,
            "body": "Looks good!",
        }
        mock_request.return_value = mock_response

        result = client.comment_on_issue("owner1", "repo1", 42, "Looks good!")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert (
            call_kwargs.kwargs["url"]
            == f"{API_URL}/repos/owner1/repo1/issues/42/comments"
        )
        assert call_kwargs.kwargs["json"] == {"body": "Looks good!"}
        assert result["body"] == "Looks good!"

    @patch("requests.request")
    def test_comment_on_issue_markdown_body(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 101, "body": "## Review\n- LGTM"}
        mock_request.return_value = mock_response

        body = "## Review\n- LGTM"
        result = client.comment_on_issue("owner1", "repo1", 10, body)

        payload = mock_request.call_args.kwargs["json"]
        assert payload["body"] == body
        assert result["body"] == body

    @patch("requests.request")
    def test_comment_on_issue_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "issue not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="issue not found"):
            client.comment_on_issue("owner1", "repo1", 9999, "comment")


if __name__ == "__main__":
    pytest.main([__file__])
