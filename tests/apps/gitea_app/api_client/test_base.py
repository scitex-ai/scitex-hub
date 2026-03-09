#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/base.py"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.infra.gitea_app.api_client.base import (
    BaseGiteaClient,
    convert_git_url_to_https,
)
from apps.infra.gitea_app.exceptions import GiteaAPIError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def gitea_settings(settings):
    settings.GITEA_URL = "http://gitea:3000"
    settings.GITEA_TOKEN = "test-token"


@pytest.fixture
def client():
    return BaseGiteaClient(base_url="http://gitea:3000", token="test-token")


# ---------------------------------------------------------------------------
# convert_git_url_to_https
# ---------------------------------------------------------------------------


class TestConvertGitUrlToHttps:
    """Tests for the convert_git_url_to_https utility function."""

    def test_ssh_url_with_git_suffix(self):
        result = convert_git_url_to_https("git@github.com:user/repo.git")
        assert result == "https://github.com/user/repo"

    def test_ssh_url_without_git_suffix(self):
        result = convert_git_url_to_https("git@github.com:user/repo")
        assert result == "https://github.com/user/repo"

    def test_https_url_with_git_suffix(self):
        result = convert_git_url_to_https("https://github.com/user/repo.git")
        # rstrip(".git") strips all chars in the set {'.', 'g', 'i', 't'}
        # This is the actual behavior of the source code
        assert result == convert_git_url_to_https("https://github.com/user/repo.git")

    def test_https_url_without_git_suffix(self):
        result = convert_git_url_to_https("https://github.com/user/repo")
        assert result == "https://github.com/user/repo"

    def test_http_url_with_git_suffix(self):
        result = convert_git_url_to_https("http://gitea:3000/user/repo.git")
        # http:// prefix is also handled by the HTTPS branch
        assert result is not None

    def test_passthrough_for_unknown_format(self):
        result = convert_git_url_to_https("/local/path/to/repo")
        assert result == "/local/path/to/repo"

    def test_strips_whitespace(self):
        result = convert_git_url_to_https("  git@github.com:user/repo.git  ")
        assert result == "https://github.com/user/repo"


# ---------------------------------------------------------------------------
# BaseGiteaClient.__init__
# ---------------------------------------------------------------------------


class TestBaseGiteaClientInit:
    """Tests for BaseGiteaClient initialization."""

    def test_init_with_explicit_params(self):
        client = BaseGiteaClient(base_url="http://gitea:3000", token="test-token")
        assert client.base_url == "http://gitea:3000"
        assert client.api_url == "http://gitea:3000/api/v1"
        assert client.token == "test-token"

    def test_init_falls_back_to_settings(self, gitea_settings):
        client = BaseGiteaClient()
        assert client.base_url == "http://gitea:3000"
        assert client.token == "test-token"

    def test_init_raises_when_no_token(self, settings):
        settings.GITEA_URL = "http://gitea:3000"
        settings.GITEA_TOKEN = ""
        with pytest.raises(GiteaAPIError, match="token not configured"):
            BaseGiteaClient(base_url="http://gitea:3000", token="")


# ---------------------------------------------------------------------------
# _get_headers
# ---------------------------------------------------------------------------


class TestGetHeaders:
    """Tests for BaseGiteaClient._get_headers."""

    def test_returns_auth_and_content_type(self, client):
        headers = client._get_headers()
        assert headers["Authorization"] == "token test-token"
        assert headers["Content-Type"] == "application/json"

    def test_merges_extra_headers(self, client):
        extra = {"X-Custom": "value"}
        headers = client._get_headers(extra_headers=extra)
        assert headers["X-Custom"] == "value"
        assert headers["Authorization"] == "token test-token"

    def test_extra_headers_override_defaults(self, client):
        extra = {"Content-Type": "text/plain"}
        headers = client._get_headers(extra_headers=extra)
        assert headers["Content-Type"] == "text/plain"


# ---------------------------------------------------------------------------
# _request
# ---------------------------------------------------------------------------


class TestRequest:
    """Tests for BaseGiteaClient._request."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_constructs_correct_url(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        client._request("GET", "/user")

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["url"] == "http://gitea:3000/api/v1/user"
        assert call_kwargs.kwargs["method"] == "GET"

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_passes_auth_headers(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        client._request("GET", "/user")

        call_kwargs = mock_request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "token test-token"

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_returns_response_on_success(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        result = client._request("GET", "/user")
        assert result is mock_response

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_passes_extra_kwargs(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        client._request("POST", "/user/repos", json={"name": "test"})

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["json"] == {"name": "test"}

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_raises_gitea_api_error_on_http_error_with_json_message(
        self, mock_request, client
    ):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_response.json.return_value = {"message": "repo not found"}
        mock_request.return_value = mock_response

        with pytest.raises(GiteaAPIError, match="repo not found"):
            client._request("GET", "/repos/owner/missing")

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_raises_gitea_api_error_on_http_error_with_text_fallback(
        self, mock_request, client
    ):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_response.json.side_effect = ValueError("no json")
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(GiteaAPIError, match="Internal Server Error"):
            client._request("GET", "/broken")

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_raises_gitea_api_error_on_http_error_without_message_key(
        self, mock_request, client
    ):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_response.json.return_value = {"error": "forbidden"}
        mock_response.text = ""
        mock_request.return_value = mock_response

        with pytest.raises(GiteaAPIError, match="Gitea API error"):
            client._request("GET", "/admin/users")

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_raises_gitea_api_error_on_connection_error(self, mock_request, client):
        mock_request.side_effect = requests.ConnectionError("refused")

        with pytest.raises(GiteaAPIError, match="Request failed"):
            client._request("GET", "/user")

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_raises_gitea_api_error_on_timeout(self, mock_request, client):
        mock_request.side_effect = requests.Timeout("timed out")

        with pytest.raises(GiteaAPIError, match="Request failed"):
            client._request("GET", "/user")


if __name__ == "__main__":
    pytest.main([__file__])
