#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/files.py"""

import base64
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.infra.gitea_app.api_client.client import GiteaClient
from apps.infra.gitea_app.exceptions import GiteaAPIError

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


class TestGetFileContents:
    """Tests for FileOperationsMixin.get_file_contents"""

    @patch("requests.request")
    def test_get_file_contents_default_ref(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "name": "README.md",
            "content": base64.b64encode(b"Hello").decode(),
            "sha": "abc123",
        }
        mock_request.return_value = mock_response

        result = client.get_file_contents("owner1", "repo1", "README.md")

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert (
            call_kwargs.kwargs["url"]
            == f"{API_URL}/repos/owner1/repo1/contents/README.md"
        )
        assert call_kwargs.kwargs["params"] == {"ref": "main"}
        assert result["name"] == "README.md"
        assert result["sha"] == "abc123"

    @patch("requests.request")
    def test_get_file_contents_custom_ref(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"name": "file.py", "sha": "def456"}
        mock_request.return_value = mock_response

        result = client.get_file_contents(
            "owner1", "repo1", "src/file.py", ref="develop"
        )

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["params"] == {"ref": "develop"}
        assert result["name"] == "file.py"

    @patch("requests.request")
    def test_get_file_contents_nested_path(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"name": "deep.txt"}
        mock_request.return_value = mock_response

        client.get_file_contents("owner1", "repo1", "a/b/c/deep.txt")

        call_kwargs = mock_request.call_args
        assert (
            call_kwargs.kwargs["url"]
            == f"{API_URL}/repos/owner1/repo1/contents/a/b/c/deep.txt"
        )

    @patch("requests.request")
    def test_get_file_contents_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "file not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="file not found"):
            client.get_file_contents("owner1", "repo1", "missing.txt")


class TestListFiles:
    """Tests for FileOperationsMixin.list_files"""

    @patch("requests.request")
    def test_list_files_root(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"name": "README.md", "type": "file"},
            {"name": "src", "type": "dir"},
        ]
        mock_request.return_value = mock_response

        result = client.list_files("owner1", "repo1")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/contents"
        assert call_kwargs.kwargs["params"] == {"ref": "main"}
        assert len(result) == 2
        assert result[0]["name"] == "README.md"

    @patch("requests.request")
    def test_list_files_with_path(self, mock_request, client, mock_response):
        mock_response.json.return_value = [{"name": "module.py", "type": "file"}]
        mock_request.return_value = mock_response

        result = client.list_files("owner1", "repo1", path="src/lib")

        call_kwargs = mock_request.call_args
        assert (
            call_kwargs.kwargs["url"]
            == f"{API_URL}/repos/owner1/repo1/contents/src/lib"
        )
        assert len(result) == 1

    @patch("requests.request")
    def test_list_files_custom_ref(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client.list_files("owner1", "repo1", ref="v1.0")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["params"] == {"ref": "v1.0"}

    @patch("requests.request")
    def test_list_files_empty_path_uses_root(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client.list_files("owner1", "repo1", path="")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/contents"

    @patch("requests.request")
    def test_list_files_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "internal error"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="internal error"):
            client.list_files("owner1", "repo1")


class TestCreateFile:
    """Tests for FileOperationsMixin.create_file"""

    @patch("requests.request")
    def test_create_file_basic(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "content": {"name": "new.txt", "sha": "aaa111"}
        }
        mock_request.return_value = mock_response

        result = client.create_file(
            "owner1", "repo1", "new.txt", "file content", message="add new.txt"
        )

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert (
            call_kwargs.kwargs["url"]
            == f"{API_URL}/repos/owner1/repo1/contents/new.txt"
        )

        payload = call_kwargs.kwargs["json"]
        assert payload["content"] == base64.b64encode(b"file content").decode()
        assert payload["message"] == "add new.txt"
        assert payload["branch"] == "main"
        assert result["content"]["name"] == "new.txt"

    @patch("requests.request")
    def test_create_file_base64_encoding(self, mock_request, client, mock_response):
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        content = "print('hello world')\n"
        client.create_file("owner1", "repo1", "hello.py", content)

        payload = mock_request.call_args.kwargs["json"]
        decoded = base64.b64decode(payload["content"]).decode()
        assert decoded == content

    @patch("requests.request")
    def test_create_file_default_message(self, mock_request, client, mock_response):
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.create_file("owner1", "repo1", "path/to/file.txt", "data")

        payload = mock_request.call_args.kwargs["json"]
        assert payload["message"] == "Create path/to/file.txt"

    @patch("requests.request")
    def test_create_file_custom_branch(self, mock_request, client, mock_response):
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.create_file("owner1", "repo1", "f.txt", "data", branch="develop")

        payload = mock_request.call_args.kwargs["json"]
        assert payload["branch"] == "develop"

    @patch("requests.request")
    def test_create_file_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 422
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "file already exists"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="file already exists"):
            client.create_file("owner1", "repo1", "existing.txt", "data")


class TestUpdateFile:
    """Tests for FileOperationsMixin.update_file"""

    @patch("requests.request")
    def test_update_file_basic(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "content": {"name": "file.txt", "sha": "bbb222"}
        }
        mock_request.return_value = mock_response

        result = client.update_file(
            "owner1",
            "repo1",
            "file.txt",
            "new content",
            sha="abc123",
            message="update file",
        )

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "PUT"
        assert (
            call_kwargs.kwargs["url"]
            == f"{API_URL}/repos/owner1/repo1/contents/file.txt"
        )

        payload = call_kwargs.kwargs["json"]
        assert payload["content"] == base64.b64encode(b"new content").decode()
        assert payload["sha"] == "abc123"
        assert payload["message"] == "update file"
        assert payload["branch"] == "main"
        assert result["content"]["sha"] == "bbb222"

    @patch("requests.request")
    def test_update_file_sha_required_in_payload(
        self, mock_request, client, mock_response
    ):
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.update_file("owner1", "repo1", "f.txt", "data", sha="sha_value_here")

        payload = mock_request.call_args.kwargs["json"]
        assert "sha" in payload
        assert payload["sha"] == "sha_value_here"

    @patch("requests.request")
    def test_update_file_default_message(self, mock_request, client, mock_response):
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.update_file("owner1", "repo1", "path/file.md", "data", sha="aaa")

        payload = mock_request.call_args.kwargs["json"]
        assert payload["message"] == "Update path/file.md"

    @patch("requests.request")
    def test_update_file_custom_branch(self, mock_request, client, mock_response):
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.update_file(
            "owner1", "repo1", "f.txt", "data", sha="aaa", branch="feature"
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["branch"] == "feature"

    @patch("requests.request")
    def test_update_file_api_error_conflict(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 409
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "sha does not match"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="sha does not match"):
            client.update_file("owner1", "repo1", "f.txt", "data", sha="wrong_sha")


if __name__ == "__main__":
    pytest.main([__file__])
