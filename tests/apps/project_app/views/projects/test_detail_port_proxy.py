#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security regression tests for the removed localhost port proxy.

CodeQL py/partial-ssrf #9385 (apps/infra/project_app/utils/port_proxy.py:81).

The project detail view used to carry a ``?port=`` branch that forwarded the
request to ``http://127.0.0.1:<port>``. Two properties made it critical:

1. ``PortProxyManager.validate_port`` checked a NUMERIC RANGE (10000-20000)
   and nothing else -- no owner, no tenant, no registry. A port number is not
   a capability.
2. The branch sat AFTER ``if request.user.is_authenticated: return ...``, so
   it was reachable ONLY by anonymous visitors on a public project. The check
   was inverted: the feature never served the users it was written for, and
   served only unauthenticated callers.

These tests pin the reachability, not the implementation: they stand up a real
victim HTTP service on a port inside the old allowed range and assert the hub
never connects to it. They fail (victim receives a request) against the code as
it stood at 98c1295.
"""

from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.infra.project_app.models import Project

# The range the deleted proxy accepted. The victim must live INSIDE it,
# otherwise the test would pass for the wrong reason (rejected as
# out-of-range rather than never attempted).
PROXY_MIN_PORT = 10000
PROXY_MAX_PORT = 20000

INTERNAL_SECRET = "INTERNAL-SERVICE-BODY-THAT-MUST-NEVER-REACH-A-VISITOR"


class _VictimHandler(BaseHTTPRequestHandler):
    """Stands in for an unauthenticated internal service (Jupyter, TensorBoard)."""

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        self.server.received_paths.append(self.path)
        body = INTERNAL_SECRET.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):  # silence stderr noise
        return


def _serve_on_a_port_in_range() -> ThreadingHTTPServer:
    """Bind a victim service inside the old proxy's allowed port range.

    THREADING, deliberately. The vulnerable proxy called requests with
    ``stream=True`` and never drained the body, so a single-threaded victim
    stayed wedged in that handler and the NEXT test hung instead of failing.
    A hang is not a test result -- it hides the very finding this file exists
    to pin.
    """
    for port in range(PROXY_MIN_PORT, PROXY_MAX_PORT + 1):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), _VictimHandler)
        except OSError:
            continue
        server.received_paths = []
        return server
    pytest.skip(f"no free port in {PROXY_MIN_PORT}-{PROXY_MAX_PORT} to bind a victim on")


def _probe(port: int) -> str:
    """Talk to the victim directly, bypassing Django entirely."""
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(b"GET /probe HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        return sock.recv(4096).decode(errors="replace")


class AnonymousPortProxySSRFTests(TestCase):
    """An anonymous visitor must not be able to steer the hub at localhost."""

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="ssrf-owner",
            email="ssrf-owner@example.com",
            password="not-used-by-these-tests",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            name="Public Project",
            slug="public-project",
            visibility="public",
        )

        self.victim = _serve_on_a_port_in_range()
        self.victim_port = self.victim.server_address[1]
        self.victim_thread = threading.Thread(
            target=self.victim.serve_forever, daemon=True
        )
        self.victim_thread.start()
        self.addCleanup(self._stop_victim)

        self.url = f"/{self.owner.username}/{self.project.slug}/"

    def _stop_victim(self):
        self.victim.shutdown()
        self.victim.server_close()
        self.victim_thread.join(timeout=5)

    # -- preconditions -----------------------------------------------------
    # Without these, a green result could come from the fixture rather than
    # from the fix: an unreachable victim, or a project the decorator refuses
    # anonymously, would pass this suite while the hole stayed open.

    def test_precondition_victim_serves_its_secret_on_that_port(self):
        """Positive control: the victim really does answer on 127.0.0.1:<port>."""
        # Arrange
        port = self.victim_port
        # Act
        payload = _probe(port)
        # Assert
        assert INTERNAL_SECRET in payload

    def test_precondition_victim_records_the_paths_it_is_asked_for(self):
        """Positive control: received_paths is a real witness, not always empty."""
        # Arrange
        self.victim.received_paths.clear()
        # Act
        _probe(self.victim_port)
        # Assert
        assert self.victim.received_paths == ["/probe"]

    def test_precondition_anonymous_may_view_the_public_project(self):
        """Positive control: the decorator DOES admit anonymous callers here.

        If it did not, the SSRF tests below would pass vacuously -- blocked at
        the door rather than at the proxy.
        """
        # Arrange
        client = Client()
        # Act
        response = client.get(self.url)
        # Assert
        assert response.status_code == 200

    # -- the regression ----------------------------------------------------

    def test_anonymous_port_param_does_not_reach_the_internal_service(self):
        """?port= must not make the hub connect to a localhost service."""
        # Arrange
        self.victim.received_paths.clear()
        # Act
        Client().get(self.url, {"port": self.victim_port})
        # Assert
        assert self.victim.received_paths == [], (
            f"the hub connected to 127.0.0.1:{self.victim_port} on behalf of "
            f"an anonymous visitor -- paths reached: {self.victim.received_paths}"
        )

    def test_anonymous_port_param_does_not_leak_the_internal_body(self):
        """Even if something connects, the internal body must not be relayed."""
        # Arrange
        self.victim.received_paths.clear()
        # Act
        response = Client().get(self.url, {"port": self.victim_port})
        # Assert
        assert INTERNAL_SECRET not in response.content.decode(errors="replace")

    def test_anonymous_port_param_does_not_forward_a_post_body(self):
        """The old branch forwarded arbitrary POST/PUT/PATCH bodies too."""
        # Arrange
        self.victim.received_paths.clear()
        # Act
        Client().post(
            self.url,
            data="{}",
            content_type="application/json",
            QUERY_STRING=f"port={self.victim_port}",
        )
        # Assert
        assert self.victim.received_paths == [], (
            f"the hub forwarded an anonymous POST to 127.0.0.1:{self.victim_port}"
        )


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
