#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/webhooks.py"""

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


class TestListOrgWebhooks:
    """Tests for WebhookOperationsMixin.list_org_webhooks"""

    @patch("requests.request")
    def test_list_org_webhooks(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"id": 1, "type": "gitea", "active": True},
            {"id": 2, "type": "gitea", "active": False},
        ]
        mock_request.return_value = mock_response

        result = client.list_org_webhooks("my-org")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org/hooks"
        assert len(result) == 2
        assert result[0]["active"] is True

    @patch("requests.request")
    def test_list_org_webhooks_empty(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = client.list_org_webhooks("no-hooks-org")

        assert result == []

    @patch("requests.request")
    def test_list_org_webhooks_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 403
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "forbidden"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="forbidden"):
            client.list_org_webhooks("restricted-org")


class TestCreateOrgWebhook:
    """Tests for WebhookOperationsMixin.create_org_webhook"""

    @patch("requests.request")
    def test_create_org_webhook_basic(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "id": 10,
            "type": "gitea",
            "active": True,
            "events": ["push"],
        }
        mock_request.return_value = mock_response

        result = client.create_org_webhook(
            "my-org",
            "https://example.com/webhook",
            ["push"],
        )

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org/hooks"

        payload = call_kwargs.kwargs["json"]
        assert payload["type"] == "gitea"
        assert payload["active"] is True
        assert payload["events"] == ["push"]
        assert payload["config"]["url"] == "https://example.com/webhook"
        assert payload["config"]["content_type"] == "json"
        assert "secret" not in payload["config"]
        assert result["id"] == 10

    @patch("requests.request")
    def test_create_org_webhook_with_secret(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 11}
        mock_request.return_value = mock_response

        client.create_org_webhook(
            "my-org",
            "https://example.com/hook",
            ["push", "pull_request"],
            secret="my-secret-key",  # pragma: allowlist secret
        )

        payload = mock_request.call_args.kwargs["json"]
        expected_secret = "my-secret-key"  # pragma: allowlist secret
        assert payload["config"]["secret"] == expected_secret
        assert payload["events"] == ["push", "pull_request"]

    @patch("requests.request")
    def test_create_org_webhook_inactive(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 12, "active": False}
        mock_request.return_value = mock_response

        client.create_org_webhook(
            "my-org",
            "https://example.com/hook",
            ["push"],
            active=False,
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["active"] is False

    @patch("requests.request")
    def test_create_org_webhook_form_content_type(
        self, mock_request, client, mock_response
    ):
        mock_response.json.return_value = {"id": 13}
        mock_request.return_value = mock_response

        client.create_org_webhook(
            "my-org",
            "https://example.com/hook",
            ["push"],
            content_type="form",
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["config"]["content_type"] == "form"

    @patch("requests.request")
    def test_create_org_webhook_multiple_events(
        self, mock_request, client, mock_response
    ):
        mock_response.json.return_value = {"id": 14}
        mock_request.return_value = mock_response

        events = ["push", "pull_request", "issues", "create", "delete"]
        client.create_org_webhook("my-org", "https://example.com/hook", events)

        payload = mock_request.call_args.kwargs["json"]
        assert payload["events"] == events

    @patch("requests.request")
    def test_create_org_webhook_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 422
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "invalid webhook URL"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="invalid webhook URL"):
            client.create_org_webhook("my-org", "not-a-url", ["push"])


class TestDeleteOrgWebhook:
    """Tests for WebhookOperationsMixin.delete_org_webhook"""

    @patch("requests.request")
    def test_delete_org_webhook(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        client.delete_org_webhook("my-org", 10)

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "DELETE"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/orgs/my-org/hooks/10"

    @patch("requests.request")
    def test_delete_org_webhook_returns_none(self, mock_request, client, mock_response):
        mock_request.return_value = mock_response

        result = client.delete_org_webhook("my-org", 10)

        assert result is None

    @patch("requests.request")
    def test_delete_org_webhook_not_found(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "hook not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="hook not found"):
            client.delete_org_webhook("my-org", 999)


class TestListRepoWebhooks:
    """Tests for WebhookOperationsMixin.list_repo_webhooks"""

    @patch("requests.request")
    def test_list_repo_webhooks(self, mock_request, client, mock_response):
        mock_response.json.return_value = [
            {"id": 20, "type": "gitea", "active": True},
        ]
        mock_request.return_value = mock_response

        result = client.list_repo_webhooks("owner1", "repo1")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/hooks"
        assert len(result) == 1
        assert result[0]["id"] == 20

    @patch("requests.request")
    def test_list_repo_webhooks_empty(self, mock_request, client, mock_response):
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = client.list_repo_webhooks("owner1", "repo1")

        assert result == []

    @patch("requests.request")
    def test_list_repo_webhooks_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "repository not found"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="repository not found"):
            client.list_repo_webhooks("owner1", "nonexistent")


class TestCreateRepoWebhook:
    """Tests for WebhookOperationsMixin.create_repo_webhook"""

    @patch("requests.request")
    def test_create_repo_webhook_basic(self, mock_request, client, mock_response):
        mock_response.json.return_value = {
            "id": 30,
            "type": "gitea",
            "active": True,
            "events": ["push"],
        }
        mock_request.return_value = mock_response

        result = client.create_repo_webhook(
            "owner1",
            "repo1",
            "https://ci.example.com/hook",
            ["push"],
        )

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert call_kwargs.kwargs["url"] == f"{API_URL}/repos/owner1/repo1/hooks"

        payload = call_kwargs.kwargs["json"]
        assert payload["type"] == "gitea"
        assert payload["active"] is True
        assert payload["events"] == ["push"]
        assert payload["config"]["url"] == "https://ci.example.com/hook"
        assert payload["config"]["content_type"] == "json"
        assert "secret" not in payload["config"]
        assert result["id"] == 30

    @patch("requests.request")
    def test_create_repo_webhook_with_secret(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 31}
        mock_request.return_value = mock_response

        client.create_repo_webhook(
            "owner1",
            "repo1",
            "https://ci.example.com/hook",
            ["push", "pull_request"],
            secret="repo-secret",  # pragma: allowlist secret
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["config"]["secret"] == "repo-secret"  # pragma: allowlist secret
        assert payload["events"] == ["push", "pull_request"]

    @patch("requests.request")
    def test_create_repo_webhook_inactive(self, mock_request, client, mock_response):
        mock_response.json.return_value = {"id": 32, "active": False}
        mock_request.return_value = mock_response

        client.create_repo_webhook(
            "owner1", "repo1", "https://example.com/hook", ["push"], active=False
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["active"] is False

    @patch("requests.request")
    def test_create_repo_webhook_form_content_type(
        self, mock_request, client, mock_response
    ):
        mock_response.json.return_value = {"id": 33}
        mock_request.return_value = mock_response

        client.create_repo_webhook(
            "owner1", "repo1", "https://example.com/hook", ["push"], content_type="form"
        )

        payload = mock_request.call_args.kwargs["json"]
        assert payload["config"]["content_type"] == "form"

    @patch("requests.request")
    def test_create_repo_webhook_api_error(self, mock_request, client):
        http_error = requests.HTTPError()
        error_response = MagicMock(spec=requests.Response)
        error_response.status_code = 422
        error_response.raise_for_status.side_effect = http_error
        error_response.json.return_value = {"message": "invalid URL scheme"}
        mock_request.return_value = error_response

        with pytest.raises(GiteaAPIError, match="invalid URL scheme"):
            client.create_repo_webhook("owner1", "repo1", "ftp://bad", ["push"])


if __name__ == "__main__":
    pytest.main([__file__])
