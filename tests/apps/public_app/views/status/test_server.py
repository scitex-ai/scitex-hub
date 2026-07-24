#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deadline tests for apps/infra/public_app/views/status/server.py.

Contract under test (fix/server-status-deadline):
- the WHOLE check pool shares one hard deadline; the page's TTFB never
  waits for a stuck check (prod measurement: crossref_local.info() at
  17.59 s dragged /server-status/ to 17-21 s TTFB while every other
  check finished in <=1 s);
- a check that misses the deadline is represented three-valued as
  UNKNOWN — status "unknown", a loud banner entry naming the check and
  the deadline — never silently dropped, never faked as up or down;
- checks that DID finish within the deadline are still merged;
- stragglers finish in the background on private dicts and cannot
  mutate the already-rendered page data.

No mock library: the check registry and deadline are INJECTED into the
view (hand-rolled fakes), and rendering goes through the real template.
"""

import time

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase

import apps.infra.public_app.views.status.server as server

URL = "/server-status/"
# Deadline for tests WITH a stuck check: generous enough that fast fakes
# always beat it even on a loaded machine, far below SLOW_S.
DEADLINE_S = 1.5
# Deadline for all-fast tests: wait() returns as soon as every check
# finishes, so a wide deadline costs nothing and kills load flakiness.
FAST_DEADLINE_S = 30.0
SLOW_S = 8.0


def _noop_check(status_data):
    """Fast fake: leaves its private status dict untouched."""


def _noop_visitor_check(request, status_data):
    """Fast fake for the (request, status_data)-taking visitor check."""


def _database_marker_check(status_data):
    """Fast fake that writes a recognisable database result."""
    status_data["database"] = {
        "is_running": True,
        "status": "connected",
        "health_class": "healthy",
    }


def _slow_check(status_data):
    """Stuck check: sleeps well past the pool deadline."""
    time.sleep(SLOW_S)


def _make_checks(slow_name=None):
    """Hand-rolled fake registry mirroring server._CHECK_PLACEMENTS."""
    checks = {}
    for name in server._CHECK_PLACEMENTS:
        if name == slow_name:
            checks[name] = _slow_check
        elif name == "check_visitor_pool_status":
            checks[name] = _noop_visitor_check
        elif name == "check_database":
            checks[name] = _database_marker_check
        else:
            checks[name] = _noop_check
    return checks


def _status_request():
    """A real GET request with session + anonymous user attached."""
    request = RequestFactory().get(URL)
    request.user = AnonymousUser()
    SessionMiddleware(lambda req: HttpResponse()).process_request(request)
    return request


class CollectorAllFastTest(SimpleTestCase):
    """No check misses the deadline: nothing is UNKNOWN."""

    def test_no_unknown_checks_recorded(self):
        # Arrange
        checks = _make_checks()
        # Act
        status_data = server._collect_status_data(None, checks, FAST_DEADLINE_S)
        # Assert
        assert status_data["unknown_checks"] == []

    def test_fast_marker_check_merged(self):
        # Arrange
        checks = _make_checks()
        # Act
        status_data = server._collect_status_data(None, checks, FAST_DEADLINE_S)
        # Assert
        assert status_data["database"]["status"] == "connected"


class CollectorSlowListCheckTest(SimpleTestCase):
    """A list-section check (package versions) sleeps past the deadline."""

    def _collect(self):
        checks = _make_checks(slow_name="check_package_versions")
        return server._collect_status_data(None, checks, DEADLINE_S)

    def test_collector_does_not_wait_for_stuck_check(self):
        # Arrange
        started = time.monotonic()
        # Act
        self._collect()
        elapsed = time.monotonic() - started
        # Assert — well under the 8 s the stuck check sleeps
        assert elapsed < 5.0, f"waited {elapsed:.2f}s for a stuck check"

    def test_unknown_check_recorded(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert
        unknown = [entry["check"] for entry in status_data["unknown_checks"]]
        assert unknown == ["check_package_versions"]

    def test_message_names_check_and_deadline(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert — message carries WHICH check and WHAT deadline it missed
        message = status_data["unknown_checks"][0]["message"]
        assert "timed out after 1.5s" in message

    def test_list_section_gets_unknown_placeholder(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert — three-valued: unknown, not missing and not failed
        assert [pkg["status"] for pkg in status_data["package_versions"]] == [
            "unknown"
        ]

    def test_fast_checks_still_merged_despite_stuck_one(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert — the deadline drops ONLY the stuck check, never the rest
        assert status_data["database"]["status"] == "connected"


class CollectorSlowDictCheckTest(SimpleTestCase):
    """A dict-section check (SLURM) sleeps past the deadline."""

    def _collect(self):
        checks = _make_checks(slow_name="check_slurm_status")
        return server._collect_status_data(None, checks, DEADLINE_S)

    def test_dict_section_status_is_unknown(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert
        assert status_data["slurm"]["status"] == "unknown"

    def test_dict_section_health_class_is_unknown(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert — dedicated third class, not healthy/unhealthy
        assert status_data["slurm"]["health_class"] == "unknown"

    def test_dict_section_error_names_deadline(self):
        # Arrange
        # Act
        status_data = self._collect()
        # Assert
        assert "timed out after 1.5s" in status_data["slurm"]["error"]


class ViewRenderTest(TestCase):
    """The real template renders the UNKNOWN state loudly."""

    def _get_response(self, slow_name=None):
        deadline = DEADLINE_S if slow_name else FAST_DEADLINE_S
        return server.server_status(
            _status_request(),
            checks=_make_checks(slow_name=slow_name),
            deadline_seconds=deadline,
        )

    def test_returns_http_200_despite_stuck_check(self):
        # Arrange
        # Act
        response = self._get_response(slow_name="check_package_versions")
        # Assert
        assert response.status_code == 200

    def test_renders_stalled_banner(self):
        # Arrange
        # Act
        response = self._get_response(slow_name="check_package_versions")
        # Assert
        assert b"Stalled Health Checks" in response.content

    def test_renders_unknown_badge(self):
        # Arrange
        # Act
        response = self._get_response(slow_name="check_package_versions")
        # Assert
        assert b"UNKNOWN" in response.content

    def test_banner_message_names_deadline(self):
        # Arrange
        # Act
        response = self._get_response(slow_name="check_package_versions")
        # Assert
        assert "timed out after 1.5s".encode() in response.content

    def test_no_stalled_banner_when_all_checks_fast(self):
        # Arrange
        # Act
        response = self._get_response()
        # Assert
        assert b"Stalled Health Checks" not in response.content


# EOF
