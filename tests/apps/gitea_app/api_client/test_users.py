#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/users.py"""

from unittest.mock import MagicMock, patch

import pytest

from apps.infra.gitea_app.api_client.client import GiteaClient
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
    return GiteaClient(base_url="http://gitea:3000", token="test-token")


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for UserOperationsMixin.get_current_user."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_calls_get_user_endpoint(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"login": "admin", "id": 1}
        mock_request.return_value = mock_response

        result = client.get_current_user()

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["url"] == "http://gitea:3000/api/v1/user"
        assert result == {"login": "admin", "id": 1}


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    """Tests for UserOperationsMixin.get_user."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_calls_users_endpoint_with_username(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"login": "testuser", "id": 42}
        mock_request.return_value = mock_response

        result = client.get_user("testuser")

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["url"] == "http://gitea:3000/api/v1/users/testuser"
        assert result == {"login": "testuser", "id": 42}


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


class TestCreateUser:
    """Tests for UserOperationsMixin.create_user."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_posts_to_admin_users_with_correct_payload(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"login": "newuser", "id": 99}
        mock_request.return_value = mock_response

        result = client.create_user("newuser", "new@example.com", "secret123")

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["url"] == "http://gitea:3000/api/v1/admin/users"
        assert call_kwargs["json"] == {
            "username": "newuser",
            "email": "new@example.com",
            "password": "secret123",  # pragma: allowlist secret
            "must_change_password": False,
        }
        assert result == {"login": "newuser", "id": 99}

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_must_change_password_flag(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"login": "newuser", "id": 99}
        mock_request.return_value = mock_response

        client.create_user(
            "newuser", "new@example.com", "secret123", must_change_password=True
        )

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["must_change_password"] is True


# ---------------------------------------------------------------------------
# user_exists
# ---------------------------------------------------------------------------


class TestUserExists:
    """Tests for UserOperationsMixin.user_exists."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_returns_true_when_user_exists(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        assert client.user_exists("existinguser") is True

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_returns_false_when_user_not_found(self, mock_request, client):
        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = req.HTTPError()
        mock_response.json.return_value = {"message": "user not found"}
        mock_request.return_value = mock_response

        assert client.user_exists("missinguser") is False

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_calls_correct_endpoint(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        client.user_exists("checkuser")

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["url"] == "http://gitea:3000/api/v1/users/checkuser"


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Tests for UserOperationsMixin.delete_user."""

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_sends_delete_to_admin_users(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        result = client.delete_user("olduser")

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "DELETE"
        assert call_kwargs["url"] == "http://gitea:3000/api/v1/admin/users/olduser"
        assert result is True

    @patch("apps.infra.gitea_app.api_client.base.requests.request")
    def test_propagates_api_error(self, mock_request, client):
        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = req.HTTPError()
        mock_response.json.return_value = {"message": "user does not exist"}
        mock_request.return_value = mock_response

        with pytest.raises(GiteaAPIError, match="user does not exist"):
            client.delete_user("ghost")


if __name__ == "__main__":
    pytest.main([__file__])
