#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SiteHealthProbe persistence (feat/persist-site-health-probes).

Covers:
- check_site_health writes one SiteHealthProbe row per run, on success
  AND on failure (a failed probe with response_time_ms=None is signal).
- collect_server_metrics deletes probe rows older than 30 days and
  keeps recent ones (same sweep as ServerMetrics retention).

No mocks (STX-NM001): the success/HTTP-error paths probe a real local
http.server; the failure path probes a real unbound localhost port.
"""

import socket
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.infra.public_app.models import SiteHealthProbe
from apps.infra.public_app.tasks.health import (
    HEALTH_CHECK_CACHE_KEY,
    HEALTH_CHECK_FAILURE_COUNT_KEY,
    check_site_health,
)
from apps.infra.public_app.tasks.metrics import collect_server_metrics


class _ProbeTargetHandler(BaseHTTPRequestHandler):
    """Minimal real HTTP endpoint for the health check to probe."""

    status = 200

    def do_GET(self):
        self.send_response(self.status)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # keep test output quiet
        pass


def _unbound_localhost_url() -> str:
    """URL on a port that is guaranteed closed (bind, read, release)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def probe_target(settings):
    """Start a real local HTTP server and point SITE_URL at it.

    Returns a function taking the status code the server should answer
    with; servers are shut down on teardown.
    """
    servers = []

    def _serve(status_code: int = 200) -> str:
        handler = type(
            "Handler", (_ProbeTargetHandler,), {"status": status_code}
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        settings.SITE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        return settings.SITE_URL

    yield _serve

    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture(autouse=True)
def _reset_health_check_state():
    """Health-check state lives in the cache; isolate each test."""
    cache.delete(HEALTH_CHECK_CACHE_KEY)
    cache.delete(HEALTH_CHECK_FAILURE_COUNT_KEY)
    yield
    cache.delete(HEALTH_CHECK_CACHE_KEY)
    cache.delete(HEALTH_CHECK_FAILURE_COUNT_KEY)


@pytest.fixture
def successful_probe(db, probe_target):
    """Row written by check_site_health against a local 200 endpoint."""
    probe_target(status_code=200)
    check_site_health()
    return SiteHealthProbe.objects.get()


@pytest.fixture
def http_error_probe(db, probe_target):
    """Row written by check_site_health against a local 500 endpoint."""
    probe_target(status_code=500)
    check_site_health()
    return SiteHealthProbe.objects.get()


@pytest.fixture
def connection_failure_probe(db, settings):
    """Row written by check_site_health against a closed port."""
    settings.SITE_URL = _unbound_localhost_url()
    check_site_health()
    return SiteHealthProbe.objects.get()


class TestCheckSiteHealthSuccessProbe:
    """A 200 probe writes one row with the measured response time."""

    def test_probe_row_is_healthy(self, successful_probe):
        # Arrange: local 200 endpoint served by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert successful_probe.is_healthy is True

    def test_probe_row_records_status_code(self, successful_probe):
        # Arrange: local 200 endpoint served by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert successful_probe.status_code == 200

    def test_probe_row_records_response_time_ms(self, successful_probe):
        # Arrange: local 200 endpoint served by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert successful_probe.response_time_ms > 0


class TestCheckSiteHealthHttpErrorProbe:
    """A non-200 probe writes a row with the status code kept."""

    def test_probe_row_is_unhealthy(self, http_error_probe):
        # Arrange: local 500 endpoint served by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert http_error_probe.is_healthy is False

    def test_probe_row_records_status_code(self, http_error_probe):
        # Arrange: local 500 endpoint served by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert http_error_probe.status_code == 500

    def test_probe_row_records_response_time_ms(self, http_error_probe):
        # Arrange: local 500 endpoint served by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert http_error_probe.response_time_ms is not None


class TestCheckSiteHealthConnectionFailureProbe:
    """A dead endpoint still writes a row — the gap is signal."""

    def test_probe_row_is_unhealthy(self, connection_failure_probe):
        # Arrange: SITE_URL pointed at a closed port by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert connection_failure_probe.is_healthy is False

    def test_probe_row_has_null_response_time(self, connection_failure_probe):
        # Arrange: SITE_URL pointed at a closed port by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert connection_failure_probe.response_time_ms is None

    def test_probe_row_has_null_status_code(self, connection_failure_probe):
        # Arrange: SITE_URL pointed at a closed port by the fixture
        # Act: check_site_health ran in the fixture
        # Assert
        assert connection_failure_probe.status_code is None


@pytest.mark.django_db
class TestCheckSiteHealthAppends:
    """Every run appends its own row — history, not a latest-value slot."""

    def test_two_runs_write_two_rows(self, probe_target):
        # Arrange
        probe_target(status_code=200)
        # Act
        check_site_health()
        check_site_health()
        # Assert
        assert SiteHealthProbe.objects.count() == 2


@pytest.mark.django_db
class TestSiteHealthProbeRetention:
    """collect_server_metrics sweeps probes >30 days, keeps recent ones."""

    def test_old_probes_deleted_recent_probes_kept(self):
        # Arrange
        now = timezone.now()
        SiteHealthProbe.objects.create(
            timestamp=now - timedelta(days=31),
            response_time_ms=100.0,
            is_healthy=True,
            status_code=200,
        )
        recent = SiteHealthProbe.objects.create(
            timestamp=now - timedelta(minutes=5),
            response_time_ms=120.0,
            is_healthy=True,
            status_code=200,
        )
        # Act
        collect_server_metrics()
        # Assert
        assert [p.pk for p in SiteHealthProbe.objects.all()] == [recent.pk]

    def test_failed_probe_rows_within_window_are_kept(self):
        # Arrange — a failure row is signal, retention must not drop it
        failed = SiteHealthProbe.objects.create(
            timestamp=timezone.now() - timedelta(days=29),
            response_time_ms=None,
            is_healthy=False,
            status_code=None,
        )
        # Act
        collect_server_metrics()
        # Assert
        assert SiteHealthProbe.objects.filter(pk=failed.pk).exists()


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
