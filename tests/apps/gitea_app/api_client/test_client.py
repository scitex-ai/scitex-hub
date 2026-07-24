#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/client.py (GiteaClient).

Default-timeout contract (fix/server-status-deadline): ``_request``
must pass a timeout to the HTTP transport even when the caller supplied
none — a wedged Gitea (observed at ~119% CPU sustained in prod) must
never hang a caller forever. An explicit caller timeout still wins.

No mock library: the HTTP transport is injected (hand-rolled recorder).
"""

from contextlib import suppress

import pytest

from apps.infra.gitea_app.api_client.base import (
    BaseGiteaClient,
    path_segment,
    repo_path,
)
from apps.infra.gitea_app.api_client.client import GiteaClient
from apps.infra.gitea_app.exceptions import GiteaAPIError


class _FakeResponse:
    """Minimal successful HTTP response."""

    status_code = 200

    def raise_for_status(self):
        """No-op: a 200 never raises."""

    def json(self):
        return {}


class _RecordingTransport:
    """Hand-rolled transport: records every call's kwargs, answers 200."""

    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse()


@pytest.fixture
def transport():
    return _RecordingTransport()


@pytest.fixture
def client(transport):
    return GiteaClient(
        base_url="http://gitea:3000", token="test-token", transport=transport
    )


class TestGiteaClientComposition:
    """GiteaClient composes the base client (and its request plumbing)."""

    def test_client_is_base_client(self):
        # Arrange
        # Act
        # Assert
        assert issubclass(GiteaClient, BaseGiteaClient)


class TestRequestDefaultTimeout:
    """_request always hands the transport a timeout."""

    def test_default_timeout_applied(self, client, transport):
        # Arrange
        # Act
        client._request("GET", "/user")
        # Assert — no caller timeout: the 10 s default is on the wire
        assert transport.calls[0]["timeout"] == 10

    def test_explicit_timeout_wins(self, client, transport):
        # Arrange
        # Act
        client._request("GET", "/user", timeout=3)
        # Assert — caller-provided timeout is never overridden
        assert transport.calls[0]["timeout"] == 3

    def test_request_reaches_transport_with_api_url(self, client, transport):
        # Arrange
        # Act
        client._request("GET", "/user")
        # Assert
        assert transport.calls[0]["url"] == "http://gitea:3000/api/v1/user"


class TestEndpointGuard:
    """SSRF choke point: _request refuses endpoints that could escape
    the API base URL — BEFORE any network call (py/partial-ssrf)."""

    def test_absolute_url_rejected(self, client):
        # Arrange
        endpoint = "http://evil.example/steal"
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="unsafe"):
            client._request("GET", endpoint)

    def test_scheme_relative_url_rejected(self, client):
        # Arrange
        endpoint = "//evil.example/steal"
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="unsafe"):
            client._request("GET", endpoint)

    def test_path_traversal_rejected(self, client):
        # Arrange
        endpoint = "/repos/../admin/users"
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="unsafe"):
            client._request("GET", endpoint)

    def test_query_smuggling_rejected(self, client):
        # Arrange
        endpoint = "/repos/x?sudo=admin"
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="unsafe"):
            client._request("GET", endpoint)

    def test_relative_endpoint_rejected(self, client):
        # Arrange
        endpoint = "user/repos"
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="unsafe"):
            client._request("GET", endpoint)

    def test_rejected_endpoint_never_reaches_transport(self, client, transport):
        # Arrange
        endpoint = "http://evil.example/steal"
        # Act — rejection itself is covered by the sibling tests
        with suppress(GiteaAPIError):
            client._request("GET", endpoint)
        # Assert
        assert transport.calls == []


class TestPathSegmentEncoding:
    """Caller-supplied segments cannot traverse to other API routes."""

    def test_path_segment_encodes_separators(self):
        # Arrange
        # Act
        encoded = path_segment("../admin/users")
        # Assert — "/" cannot survive as a separator
        assert encoded == "..%2Fadmin%2Fusers"

    def test_path_segment_rejects_empty(self):
        # Arrange
        value = ""
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="Invalid URL path segment"):
            path_segment(value)

    def test_path_segment_rejects_dot_dot(self):
        # Arrange
        value = ".."
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="Invalid URL path segment"):
            path_segment(value)

    def test_repo_path_keeps_separators(self):
        # Arrange
        # Act
        encoded = repo_path("dir/file name.txt")
        # Assert — in-repo "/" survives, everything else is encoded
        assert encoded == "dir/file%20name.txt"

    def test_repo_path_rejects_traversal_segment(self):
        # Arrange
        value = "dir/../secret"
        # Act
        # Assert
        with pytest.raises(GiteaAPIError, match="Invalid URL path segment"):
            repo_path(value)

    def test_mixin_encodes_malicious_org(self, client, transport):
        # Arrange
        # Act — a crafted org name must stay ONE encoded segment
        client.get_organization("../admin/users")
        # Assert
        assert transport.calls[0]["url"] == (
            "http://gitea:3000/api/v1/orgs/..%2Fadmin%2Fusers"
        )


# EOF
