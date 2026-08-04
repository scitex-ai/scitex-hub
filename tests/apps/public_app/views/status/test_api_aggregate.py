#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for apps/infra/public_app/views/status/api/aggregate.py.

``/api/status/`` is the JSON twin of the ``/server-status/`` page and the ONLY
door through which status.scitex.ai (a Cloudflare Worker at the edge) can see the
hub's internals. What it must guarantee:

- a DECLARED shape — schema / generated_at / deadline_seconds / complete /
  status_data — so a consumer never has to guess which key exists on this call;
- PARTIAL results reach the edge: a check that misses the deadline leaves the
  other checks intact, sets ``complete`` false, and names itself in
  ``status_data.unknown_checks`` (three-valued, never collapsed to up/down);
- the SAME check registry as the page, so the two can never drift into
  disagreeing about the same server;
- NO widening of exposure: checks outside ``_CHECK_PLACEMENTS`` are not called
  here either, so the JSON carries exactly the keys the page already renders;
- datetimes survive encoding — the visitor pool writes ``expires_at`` as a real
  datetime, which plain ``json.dumps`` refuses.

No mock library: the check registry and deadline are INJECTED, exactly as
``tests/.../test_server.py`` does for the page.
"""

import json
import time
from datetime import datetime
from datetime import timezone as dt_timezone

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

import apps.infra.public_app.views.status.server as server
from apps.infra.public_app.views.status.api import aggregate

URL = "/api/status/"
# Generous: wait() returns as soon as every fake finishes, so a wide deadline
# costs nothing and kills load flakiness on a busy machine.
FAST_DEADLINE_S = 30.0
# Tight enough that the stuck fake always misses it, wide enough that the fast
# fakes always beat it.
DEADLINE_S = 1.5
SLOW_S = 8.0

# A fixed instant, so the assertion is on the ENCODING, not on the clock.
EXPIRES_AT = datetime(2026, 8, 4, 12, 30, 0, tzinfo=dt_timezone.utc)


def _noop_check(status_data):
    """Fast fake: leaves its private status dict untouched."""


def _noop_visitor_check(request, status_data):
    """Fast fake for the (request, status_data)-taking visitor check."""


def _database_marker_check(status_data):
    """Fast fake writing a recognisable database result."""
    status_data["database"] = {
        "is_running": True,
        "status": "connected",
        "health_class": "healthy",
    }


def _visitor_datetime_check(request, status_data):
    """Fake visitor-pool check writing a real datetime, as the live one does."""
    status_data["visitor_pool"] = {
        "pool_status": {"allocated": 1, "total": 16},
        "allocations": [
            {
                "slot_number": 1,
                "status": "allocated",
                "expires_at": EXPIRES_AT,
                "minutes_remaining": 55,
                "visitor_username": "visitor-001",
                "is_current_user": False,
            }
        ],
        "session_lifetime_hours": 1,
    }


def _slow_check(status_data):
    """Stuck check: sleeps well past the pool deadline."""
    time.sleep(SLOW_S)


def _make_checks(slow_name=None, visitor_check=None):
    """Hand-rolled fake registry mirroring server._CHECK_PLACEMENTS."""
    checks = {}
    for name in server._CHECK_PLACEMENTS:
        if name == slow_name:
            checks[name] = _slow_check
        elif name == "check_visitor_pool_status":
            checks[name] = visitor_check or _noop_visitor_check
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


def _call(checks, deadline_seconds):
    """Run the endpoint and return its decoded body."""
    response = aggregate.status_api(_status_request(), checks, deadline_seconds)
    return response, json.loads(response.content.decode("utf-8"))


class DeclaredShapeTest(SimpleTestCase):
    """Every response carries the same named fields — never a shape-shifting dict."""

    def test_response_carries_exactly_the_declared_keys(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert set(body) == {
            "schema",
            "generated_at",
            "deadline_seconds",
            "complete",
            "status_data",
        }

    def test_response_declares_the_current_schema_version(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert body["schema"] == "scitex-hub.status/1"

    def test_healthy_collection_responds_http_200(self):
        # Arrange
        checks = _make_checks()
        # Act
        response, _ = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert response.status_code == 200

    def test_response_content_type_is_json(self):
        # Arrange
        checks = _make_checks()
        # Act
        response, _ = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert response["Content-Type"].startswith("application/json")

    def test_response_is_never_served_from_a_cache(self):
        """A cached status reading is a claim about the past shown as the present."""
        # Arrange
        checks = _make_checks()
        # Act
        response, _ = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert response["Cache-Control"] == "no-store"

    def test_response_reports_the_deadline_it_used(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert body["deadline_seconds"] == FAST_DEADLINE_S


class CompleteResultTest(SimpleTestCase):
    """All checks answer: complete is true and nothing is UNKNOWN."""

    def test_every_check_answering_marks_result_complete(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert body["complete"] is True

    def test_every_check_answering_leaves_unknown_list_empty(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert body["status_data"]["unknown_checks"] == []

    def test_finished_check_result_is_carried_in_payload(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert body["status_data"]["database"]["status"] == "connected"


class PartialResultTest(SimpleTestCase):
    """One stuck check must not cost the edge every other reading."""

    def test_stuck_check_marks_the_result_incomplete(self):
        # Arrange
        checks = _make_checks(slow_name="check_package_versions")
        # Act
        _, body = _call(checks, DEADLINE_S)
        # Assert
        assert body["complete"] is False

    def test_stuck_check_is_named_in_unknown_checks(self):
        # Arrange
        checks = _make_checks(slow_name="check_package_versions")
        # Act
        _, body = _call(checks, DEADLINE_S)
        # Assert
        assert [u["check"] for u in body["status_data"]["unknown_checks"]] == [
            "check_package_versions"
        ]

    def test_stuck_check_status_reads_unknown_not_down(self):
        """Three-valued: 'we could not tell' must not become 'it is broken'."""
        # Arrange
        checks = _make_checks(slow_name="check_package_versions")
        # Act
        _, body = _call(checks, DEADLINE_S)
        # Assert
        assert body["status_data"]["package_versions"][0]["status"] == "unknown"

    def test_stuck_check_health_class_reads_unknown_not_down(self):
        """The edge styles off health_class, so it must carry unknown too."""
        # Arrange
        checks = _make_checks(slow_name="check_package_versions")
        # Act
        _, body = _call(checks, DEADLINE_S)
        # Assert
        assert body["status_data"]["package_versions"][0]["health_class"] == "unknown"

    def test_other_checks_still_reach_the_edge(self):
        """The whole point of a partial-result API."""
        # Arrange
        checks = _make_checks(slow_name="check_package_versions")
        # Act
        _, body = _call(checks, DEADLINE_S)
        # Assert
        assert body["status_data"]["database"]["status"] == "connected"

    def test_stuck_check_still_responds_http_200(self):
        """A partial reading is a result, not a server error."""
        # Arrange
        checks = _make_checks(slow_name="check_package_versions")
        # Act
        response, _ = _call(checks, DEADLINE_S)
        # Assert
        assert response.status_code == 200


class DatetimeEncodingTest(SimpleTestCase):
    """The live visitor-pool check writes datetimes; json.dumps refuses those."""

    def test_visitor_slot_expiry_encodes_as_iso_string(self):
        # Arrange
        checks = _make_checks(visitor_check=_visitor_datetime_check)
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        slot = body["status_data"]["visitor_pool"]["allocations"][0]
        assert slot["expires_at"] == "2026-08-04T12:30:00Z"

    def test_visitor_slot_identity_survives_encoding(self):
        # Arrange
        checks = _make_checks(visitor_check=_visitor_datetime_check)
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        slot = body["status_data"]["visitor_pool"]["allocations"][0]
        assert slot["visitor_username"] == "visitor-001"


class NoDriftFromThePageTest(SimpleTestCase):
    """The API and the page must measure the same machine the same way."""

    def test_every_registered_check_is_resolvable_on_the_page_module(self):
        """A name in the registry with no callable behind it would raise at request
        time, on the one endpoint that must answer during an incident."""
        # Arrange
        names = list(server._CHECK_PLACEMENTS)
        # Act
        missing = [n for n in names if not callable(getattr(server, n, None))]
        # Assert
        assert missing == []

    def test_api_resolves_checks_from_the_page_module(self):
        """The drift guard: both sides must read the SAME module namespace, so a
        check swapped on the page cannot leave the API running the old one."""
        # Arrange
        expected = server
        # Act
        resolved = aggregate._server_module()
        # Assert
        assert resolved is expected

    def test_patching_a_page_check_changes_what_the_api_resolves(self):
        """Proves the resolution is live, not a snapshot taken at import time."""
        # Arrange
        original = server.check_database
        server.check_database = _database_marker_check
        # Act
        try:
            resolved = getattr(aggregate._server_module(), "check_database")
        finally:
            server.check_database = original
        # Assert
        assert resolved is _database_marker_check

    def test_api_default_deadline_is_the_pages_deadline(self):
        # Arrange
        page_deadline = server.CHECK_DEADLINE_SECONDS
        # Act
        api_deadline = aggregate.CHECK_DEADLINE_SECONDS
        # Assert
        assert api_deadline is page_deadline


class ExposureIsUnchangedTest(SimpleTestCase):
    """The JSON must carry the page's keys — not one key more."""

    def test_citation_graph_check_exists_but_is_unregistered(self):
        """Positive control: the function exists, so its absence below is real."""
        # Arrange
        from apps.infra.public_app.views.status import health_checks

        # Act
        exists = callable(health_checks.check_citation_graph)
        # Assert
        assert exists and "check_citation_graph" not in server._CHECK_PLACEMENTS

    def test_user_data_permissions_check_exists_but_is_unregistered(self):
        """Positive control for the second off-page check."""
        # Arrange
        from apps.infra.public_app.views.status import health_checks

        # Act
        exists = callable(health_checks.check_user_data_permissions)
        # Assert
        assert exists and "check_user_data_permissions" not in server._CHECK_PLACEMENTS

    def test_citation_graph_key_absent_from_payload(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert "citation_graph" not in body["status_data"]

    def test_user_data_permissions_key_absent_from_payload(self):
        # Arrange
        checks = _make_checks()
        # Act
        _, body = _call(checks, FAST_DEADLINE_S)
        # Assert
        assert "user_data_permissions" not in body["status_data"]


class RoutingTest(SimpleTestCase):
    """The endpoint the edge fetches must actually be wired."""

    def test_api_status_path_resolves_to_the_view(self):
        # Arrange
        path = URL
        # Act
        match = resolve(path)
        # Assert
        assert match.func is aggregate.status_api

    def test_named_route_reverses_to_the_api_path(self):
        # Arrange
        name = "public_app:status_api"
        # Act
        path = reverse(name)
        # Assert
        assert path == URL


# EOF
