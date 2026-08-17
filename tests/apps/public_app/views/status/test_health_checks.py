#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Gitea health probe must test AUTHENTICATION, not just reachability.

These tests exist because of a measured production incident, 2026-08-17.

The probe used to call `/api/v1/version` with no credentials. That answers
"is Gitea up?", which was never in doubt. Meanwhile the configured token had
been rotated out from under the app and never written back, so EVERY
authenticated call returned 401: visitor-slot resets failed, all 16 slots
quarantined, and every anonymous visitor on scitex.ai was downgraded to
read-only for roughly five weeks.

Throughout all of it, `gitea_api` reported `healthy`.

That is a check that cannot fail. These tests pin the behaviours that make it
able to fail.

NO MOCKS. A real HTTP server runs on localhost and answers like Gitea does --
401 for a token it does not know, 200 for one it does. The production code is
pointed at it through `settings.GITEA_API_URL`, the same setting it reads in
production. That the probe is testable this way at all is the point: it used to
hardcode `http://gitea:3000/api/v1`, which is what forced patching.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from django.test import override_settings

from apps.infra.public_app.views.status.health_checks import check_api_services

VALID_TOKEN = "the-token-gitea-knows"


class _GiteaLike(BaseHTTPRequestHandler):
    """Answers the two endpoints the probe uses, with Gitea's real semantics."""

    recorded_paths: list = []
    recorded_auth: list = []

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        type(self).recorded_paths.append(self.path)
        type(self).recorded_auth.append(self.headers.get("Authorization"))

        if self.path.endswith("/version"):
            # Gitea answers /version to anyone, credentials or not.
            self._respond(200, {"version": "1.25.2"})
        elif self.path.endswith("/user"):
            if self.headers.get("Authorization") == f"token {VALID_TOKEN}":
                self._respond(200, {"id": 1, "login": "scitex_admin"})
            else:
                self._respond(401, {"message": "invalid username, password or token"})
        else:
            self._respond(404, {"message": "not found"})

    def _respond(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        """Silence the default stderr access log."""


@pytest.fixture
def gitea_like_server():
    """A real HTTP server that behaves like Gitea. Yields its api base URL."""
    # Arrange
    _GiteaLike.recorded_paths = []
    _GiteaLike.recorded_auth = []
    server = HTTPServer(("127.0.0.1", 0), _GiteaLike)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/api/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _gitea_entry(status_data):
    return next(
        entry
        for entry in status_data["api_services"]
        if entry.get("name") == "Gitea API"
    )


def _run_probe(api_url, token):
    status_data = {}
    with override_settings(GITEA_API_URL=api_url, GITEA_TOKEN=token):
        check_api_services(status_data)
    return status_data


class TestTheProbeAuthenticates:
    def test_it_sends_the_configured_token(self, gitea_like_server):
        # Arrange
        token = VALID_TOKEN
        # Act
        _run_probe(gitea_like_server, token)
        # Assert
        assert f"token {token}" in _GiteaLike.recorded_auth

    def test_it_calls_an_endpoint_that_requires_authentication(
        self, gitea_like_server
    ):
        # Arrange
        token = VALID_TOKEN
        # Act
        _run_probe(gitea_like_server, token)
        # Assert
        assert any(path.endswith("/user") for path in _GiteaLike.recorded_paths)


class TestARejectedTokenIsReportedUnhealthy:
    """The case that went unreported for five weeks."""

    @pytest.fixture
    def rejected(self, gitea_like_server):
        """The probe's own report after Gitea refused the token."""
        return _gitea_entry(
            _run_probe(gitea_like_server, "a-token-gitea-no-longer-knows")
        )

    def test_it_is_not_running(self, rejected):
        # Arrange
        report = rejected
        # Act
        value = report
        # Assert
        assert value["is_running"] is False

    def test_it_is_classed_unhealthy(self, rejected):
        # Arrange
        report = rejected
        # Act
        value = report
        # Assert
        assert value["health_class"] == "unhealthy"

    def test_the_message_names_the_status_code(self, rejected):
        # Arrange
        report = rejected
        # Act
        value = report
        # Assert
        assert "401" in value["details"]

    def test_the_message_names_the_setting_to_fix(self, rejected):
        # Arrange
        report = rejected
        # Act
        value = report
        # Assert
        assert "SCITEX_HUB_GITEA_TOKEN" in value["details"]

    def test_the_message_names_the_repair_script(self, rejected):
        # Arrange
        report = rejected
        # Act
        value = report
        # Assert
        assert "regenerate-gitea-token.sh" in value["details"]

    def test_the_message_names_the_user_visible_consequence(self, rejected):
        """An error that only states what broke is half-written."""
        # Arrange
        report = rejected
        # Act
        value = report
        # Assert
        assert "Visitor-slot resets will fail" in value["details"]


class TestTheHealthyCaseStillPasses:
    """A guard that fails on everything is as useless as one that fails on nothing."""

    @pytest.fixture
    def accepted(self, gitea_like_server):
        """The probe's own report after Gitea accepted the token."""
        return _gitea_entry(_run_probe(gitea_like_server, VALID_TOKEN))

    def test_it_is_running(self, accepted):
        # Arrange
        report = accepted
        # Act
        value = report
        # Assert
        assert value["is_running"] is True

    def test_it_is_classed_healthy(self, accepted):
        # Arrange
        report = accepted
        # Act
        value = report
        # Assert
        assert value["health_class"] == "healthy"


class TestNoTokenConfigured:
    """Absence of a token must not be reported as a passing auth check."""

    def test_it_falls_back_to_the_liveness_endpoint(self, gitea_like_server):
        # Arrange
        no_token = ""
        # Act
        _run_probe(gitea_like_server, no_token)
        # Assert
        assert any(path.endswith("/version") for path in _GiteaLike.recorded_paths)

    def test_it_says_authentication_was_not_tested(self, gitea_like_server):
        # Arrange
        no_token = ""
        # Act
        entry = _gitea_entry(_run_probe(gitea_like_server, no_token))
        # Assert
        assert "not tested" in entry["details"]


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
