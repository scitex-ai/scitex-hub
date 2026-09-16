#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Who may see the host behind /server-status/ (site audit 2026-09-14).

Defect: every status endpoint answered 200 to a signed-out visitor with the
host's CPU / memory / disk / network counters and 24 h of history. Decision:
- the public status view stays public — /api/public-status/, and a service
  list on /server-status/ for non-admins, with no chart and no chart script
  (so the page never calls an admin-only endpoint and never logs a 403);
- host metrics (realtime, history, CSV export, chart series) are instance-admin
  only and answer 403 JSON to everyone else;
- /api/status/ keeps its declared shape for everyone, but a non-admin gets
  per-service state only.

Real Django test client and real test DB; the public-status cache is SEEDED so
the page does not run live network checks. No mocks.
"""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.infra.public_app.views.status.api import aggregate
from apps.infra.public_app.views.status.public_status import PUBLIC_STATUS_CACHE_KEY

SERVER_STATUS_API = "/api/server-status/"
HISTORY_API = "/api/server-metrics/history/"
SERIES_API = "/api/server-metrics/series/"
EXPORT_API = "/api/server-metrics/export/"
PUBLIC_STATUS_API = "/api/public-status/"
STATUS_PAGE = "/server-status/"

PUBLIC_STATUS_FIXTURE = {
    "overall": "operational",
    "services": [
        {
            "name": "Web Application",
            "status": "operational",
            "uptime_days": ["operational"] * 90,
            "uptime_pct": "100.00",
        }
    ],
    "checked_at": "2026-09-14T18:00:00+00:00",
}

FULL_STATUS_DATA = {
    "unknown_checks": [{"name": "SLURM", "check": "check_slurm_status", "message": "x"}],
    "services": [
        {"name": "django", "status": "running", "health_class": "healthy", "image": "hub:1.2.3"}
    ],
    "ssh_services": [],
    "api_services": [
        dict(name="Gitea", status="up", health_class="healthy", url="http://10.0.0.5:3000")
    ],
    "database": {"status": "connected", "health_class": "healthy", "name": "scitex_prod"},
    "redis": {},
    "disk": {"percent_used": 55.0},
    "system": {"cpu_percent": 12.5, "memory_percent": 40.0},
    "package_versions": [{"name": "scitex", "version": "2.0.0"}],
}


def _make_user(username, **flags):
    return get_user_model().objects.create_user(username=username, password="x", **flags)


class _SeededPublicStatus(TestCase):
    """Seed the public-status cache so no live health check runs."""

    def setUp(self):
        super().setUp()
        cache.set(PUBLIC_STATUS_CACHE_KEY, PUBLIC_STATUS_FIXTURE, 300)

    def tearDown(self):
        cache.delete(PUBLIC_STATUS_CACHE_KEY)
        super().tearDown()


class HostMetricsApisAreAdminOnlyTest(TestCase):
    def test_anonymous_server_status_api_is_403(self):
        # Arrange
        url = SERVER_STATUS_API
        # Act
        response = self.client.get(url)
        # Assert
        assert response.status_code == 403

    def test_anonymous_403_is_json_with_a_message(self):
        # Arrange
        url = SERVER_STATUS_API
        # Act
        body = json.loads(self.client.get(url).content)
        # Assert
        assert body["detail"].startswith("Host metrics are available to instance")

    def test_anonymous_403_carries_no_cpu_reading(self):
        # Arrange
        url = SERVER_STATUS_API
        # Act
        body = json.loads(self.client.get(url).content)
        # Assert
        assert "cpu_percent" not in body

    def test_signed_in_non_admin_server_status_api_is_403(self):
        # Arrange
        self.client.force_login(_make_user("plain-user"))
        # Act
        response = self.client.get(SERVER_STATUS_API)
        # Assert
        assert response.status_code == 403

    def test_staff_server_status_api_is_200(self):
        # Arrange
        self.client.force_login(_make_user("staff-user", is_staff=True))
        # Act
        response = self.client.get(SERVER_STATUS_API)
        # Assert
        assert response.status_code == 200

    def test_staff_server_status_api_has_no_visitor_capacity_fields(self):
        self.client.force_login(_make_user("staff-capacity-user", is_staff=True))
        body = json.loads(self.client.get(SERVER_STATUS_API).content)
        assert not any(key.startswith("visitor_pool") for key in body)

    def test_superuser_server_status_api_is_200(self):
        # Arrange
        self.client.force_login(_make_user("root-user", is_superuser=True))
        # Act
        response = self.client.get(SERVER_STATUS_API)
        # Assert
        assert response.status_code == 200

    def test_anonymous_history_api_is_403(self):
        # Arrange
        url = HISTORY_API
        # Act
        response = self.client.get(url)
        # Assert
        assert response.status_code == 403

    def test_anonymous_series_api_is_403(self):
        # Arrange
        url = SERIES_API
        # Act
        response = self.client.get(url, {"minutes": 60})
        # Assert
        assert response.status_code == 403

    def test_anonymous_csv_export_is_403(self):
        # Arrange
        url = EXPORT_API
        # Act
        response = self.client.get(url)
        # Assert
        assert response.status_code == 403


class PublicStatusStaysPublicTest(_SeededPublicStatus):
    def test_anonymous_public_status_api_is_200(self):
        # Arrange
        url = PUBLIC_STATUS_API
        # Act
        response = self.client.get(url)
        # Assert
        assert response.status_code == 200


class NonAdminStatusPageTest(_SeededPublicStatus):
    def _anonymous_page(self):
        return self.client.get(STATUS_PAGE)

    def test_anonymous_page_is_200(self):
        # Arrange
        # Act
        response = self._anonymous_page()
        # Assert
        assert response.status_code == 200

    def test_anonymous_page_renders_the_public_service_list(self):
        # Arrange — positive control for the absence assertions below
        # Act
        response = self._anonymous_page()
        # Assert
        assert b'id="publicServices"' in response.content

    def test_anonymous_page_names_a_public_service(self):
        # Arrange
        # Act
        response = self._anonymous_page()
        # Assert
        assert b"Web Application" in response.content

    def test_anonymous_page_does_not_load_the_chart_script(self):
        # Arrange
        # Act
        response = self._anonymous_page()
        # Assert
        assert b"public_app/ts/server-status" not in response.content

    def test_anonymous_page_declares_no_series_endpoint(self):
        # Arrange
        # Act
        response = self._anonymous_page()
        # Assert
        assert b"data-series-endpoint" not in response.content

    def test_anonymous_page_renders_no_chart_container(self):
        # Arrange
        # Act
        response = self._anonymous_page()
        # Assert
        assert b"metric-chart" not in response.content

    def test_signed_in_non_admin_page_has_no_chart_container(self):
        # Arrange
        self.client.force_login(_make_user("plain-page-user"))
        # Act
        response = self.client.get(STATUS_PAGE)
        # Assert
        assert b"metric-chart" not in response.content


class StatusApiRedactionTest(TestCase):
    """/api/status/ for a non-admin: same shape, per-service state only."""

    def test_system_metrics_are_dropped(self):
        # Arrange
        data = FULL_STATUS_DATA
        # Act
        redacted = aggregate.redact_for_public(data)
        # Assert
        assert "system" not in redacted

    def test_package_versions_are_dropped(self):
        # Arrange
        data = FULL_STATUS_DATA
        # Act
        redacted = aggregate.redact_for_public(data)
        # Assert
        assert "package_versions" not in redacted

    def test_container_entry_keeps_only_state(self):
        # Arrange
        data = FULL_STATUS_DATA
        # Act
        redacted = aggregate.redact_for_public(data)
        # Assert
        assert redacted["services"] == [
            {"name": "django", "status": "running", "health_class": "healthy"}
        ]

    def test_internal_api_url_is_dropped(self):
        # Arrange
        data = FULL_STATUS_DATA
        # Act
        redacted = aggregate.redact_for_public(data)
        # Assert
        assert set(redacted["api_services"][0]) == {"name", "status", "health_class"}

    def test_database_name_is_dropped(self):
        # Arrange
        data = FULL_STATUS_DATA
        # Act
        redacted = aggregate.redact_for_public(data)
        # Assert
        assert redacted["database"] == {"status": "connected", "health_class": "healthy"}

    def test_unknown_checks_still_named(self):
        # Arrange
        data = FULL_STATUS_DATA
        # Act
        redacted = aggregate.redact_for_public(data)
        # Assert
        assert redacted["unknown_checks"] == [{"name": "SLURM", "check": "check_slurm_status"}]

    def test_anonymous_status_api_payload_has_no_system_section(self):
        # Arrange
        url = "/api/status/"
        # Act
        body = json.loads(self.client.get(url).content)
        # Assert
        assert "system" not in body["status_data"]


# EOF
