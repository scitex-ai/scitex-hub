#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/gitea_app/api_client/test_create_organization_visibility.py
"""`create_organization` sends Gitea's `visibility`; `setup_registry_repo` relies on it.

WHY THIS EXISTS. On the 2026-11-27 prod release `manage.py setup_registry_repo`
died with ``TypeError: create_organization() got an unexpected keyword argument
'visibility'``: the command asked for a public `scitex-apps` organisation, and
the client had no such parameter, so the org was never created. These tests
drive the real client against a real local HTTP server (no mocks) and record
the JSON body Gitea would receive.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from apps.infra.gitea_app.api_client.client import GiteaClient


class _Recorder(BaseHTTPRequestHandler):
    bodies: list = []

    def do_POST(self):  # noqa: N802 -- http.server API
        length = int(self.headers.get("Content-Length", "0"))
        type(self).bodies.append(json.loads(self.rfile.read(length) or b"{}"))
        payload = json.dumps({"username": "recorded", "id": 1}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        return


@pytest.fixture
def gitea():
    _Recorder.bodies = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", _Recorder.bodies
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def gitea_settings(settings, gitea):
    settings.GITEA_URL = gitea[0]
    settings.GITEA_TOKEN = "local-test-only"  # pragma: allowlist secret


def test_visibility_reaches_the_create_request(gitea):
    # Arrange
    client = GiteaClient(
        base_url=gitea[0], token="local-test-only"
    )  # pragma: allowlist secret
    # Act
    client.create_organization(
        "scitex-apps", full_name="SciTeX Apps", visibility="public"
    )
    # Assert
    assert gitea[1][-1]["visibility"] == "public"


def test_omitted_visibility_leaves_gitea_default(gitea):
    # Arrange
    client = GiteaClient(
        base_url=gitea[0], token="local-test-only"
    )  # pragma: allowlist secret
    # Act
    client.create_organization("plain-org")
    # Assert
    assert "visibility" not in gitea[1][-1]


def test_unknown_visibility_is_refused_before_any_request(gitea):
    # Arrange
    client = GiteaClient(
        base_url=gitea[0], token="local-test-only"
    )  # pragma: allowlist secret
    # Act
    call = lambda: client.create_organization("x", visibility="everyone")  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        call()
