#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/gitea_app/api_client/client.py (GiteaClient).

Default-timeout contract (fix/server-status-deadline): ``_request``
must pass a timeout to the HTTP transport even when the caller supplied
none — a wedged Gitea (observed at ~119% CPU sustained in prod) must
never hang a caller forever. An explicit caller timeout still wins.

No mock library: the HTTP transport is injected (hand-rolled recorder).
"""

import pytest

from apps.infra.gitea_app.api_client.base import BaseGiteaClient
from apps.infra.gitea_app.api_client.client import GiteaClient


class _FakeResponse:
    """Minimal successful HTTP response."""

    status_code = 200

    def raise_for_status(self):
        """No-op: a 200 never raises."""


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


# EOF
