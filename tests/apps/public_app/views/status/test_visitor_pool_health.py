#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A zero-ready visitor pool must never report healthy.

WHAT WENT WRONG (2026-08-16, measured on the prod host)
For ~1h35m after a deploy, all 16 visitor slots sat quarantined and EVERY
anonymous visitor was funnelled onto the single shared ``readonly-visitor``
account. ``/api/server-health/`` reported ``{"status": "healthy", "color":
"#22c55e", "issues": []}`` the whole time — and it was not lying. Postgres,
Redis, SSH, the API probes, SLURM, apptainer, the containers and the data-dir
permissions were all genuinely fine. The endpoint was answering a question
that did not include the visitor pool.

The probe already existed: ``PoolAllocator.get_pool_status`` computes
``ready`` from exactly ``quarantined=False, is_active=False,
workspace_ready=True``. Three call sites read that dict and dropped ``ready``
on the floor. The measured state that day was ``ready=0, quarantined=16,
allocated=0`` — and ``free=16``, the number that looks perfect.

WHAT THESE TESTS PIN
- ``ready == 0`` produces overall ``"error"`` + the red ``#ef4444``, not
  ``"warning"``. ``issues[]`` renders only in the notification bell, which is
  wrapped in ``{% if DEBUG or user.is_staff %}``; the status COLOUR is the only
  part a non-staff visitor sees. Filing a total outage as a warning would
  leave the public dot green and reproduce the incident for everyone else.
- the ``issues[]`` entry NAMES THE REPAIR COMMAND. Every other entry in that
  list is a bare symptom string, and on 2026-08-16 the repair for this exact
  failure existed only inside a card comment (constitution §7).
- the named repair is the SAFE one (``--repair-only``): plain
  ``reconcile_visitor_slots`` quarantines every slot including healthy ones.
- a slot merely IN USE never raises an alarm (severity keys on
  ``quarantined``, not on ``ready < total``).

No DB and no network: ``check_visitor_pool`` takes a kwarg-only
``pool_status_fn`` seam — a tiny REAL function returning a measured status
dict, in the same spirit as the ``enqueue_fn=`` / ``clone_fn=`` seams already
used in the visitor-pool code. Nothing here is mocked; the ORM counting that
produces those numbers is covered by the pool_manager tests.
"""

from apps.infra.public_app.views.status.api.health import (
    _build_issues_list,
    _determine_overall_health,
)
from apps.infra.public_app.views.status.visitor_pool_health import (
    check_visitor_pool,
)

# The state measured on prod at 14:49Z, 2026-08-16.
OUTAGE_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 16,
    "ready": 0,
}
HEALTHY_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 0,
    "ready": 16,
}
IN_USE_STATUS = {
    "total": 16,
    "allocated": 3,
    "free": 13,
    "expired": 0,
    "quarantined": 0,
    "ready": 13,
}
DEGRADED_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 5,
    "ready": 11,
}


def _status_data_for(pool_status: dict) -> dict:
    """Run the real check with an injected status source (no DB)."""
    status_data = {"services": [], "ssh_services": [], "api_services": []}
    check_visitor_pool(status_data, pool_status_fn=lambda: pool_status)
    return status_data


class TestZeroReadyPoolIsNotHealthy:
    """The exact question nothing asked on 2026-08-16."""

    def test_zero_ready_pool_reports_error_status(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "error"

    def test_zero_ready_pool_paints_the_public_dot_red(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        _overall_status, color = _determine_overall_health(status_data)
        # Assert — the only signal a non-staff visitor can see
        assert color == "#ef4444"

    def test_zero_ready_pool_raises_a_visitor_pool_issue(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert [issue["service"] for issue in issues] == ["Visitor Pool"]

    def test_zero_ready_issue_is_error_level(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues[0]["level"] == "error"

    def test_zero_ready_issue_names_the_repair_command(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert — a symptom without a fix is the archaeology this cost us
        assert "reconcile_visitor_slots" in issues[0]["message"]

    def test_zero_ready_issue_names_the_safe_repair_flag(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert — plain reconcile quarantines healthy slots too
        assert "--repair-only" in issues[0]["message"]

    def test_zero_ready_issue_states_the_visitor_consequence(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert "readonly-visitor" in issues[0]["message"]

    def test_zero_ready_check_marks_the_pool_unhealthy(self):
        # Arrange
        status_data = _status_data_for(OUTAGE_STATUS)
        # Act
        health_class = status_data["visitor_pool"]["health_class"]
        # Assert
        assert health_class == "unhealthy"


class TestHealthyPoolStaysGreen:
    """The gate must not cry wolf, or it will be muted."""

    def test_full_pool_reports_healthy(self):
        # Arrange
        status_data = _status_data_for(HEALTHY_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "healthy"

    def test_full_pool_raises_no_issue(self):
        # Arrange
        status_data = _status_data_for(HEALTHY_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues == []

    def test_slots_in_use_do_not_raise_an_issue(self):
        # Arrange — 3 visitors are working; those slots are legitimately not ready
        status_data = _status_data_for(IN_USE_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues == []

    def test_slots_in_use_keep_overall_status_healthy(self):
        # Arrange
        status_data = _status_data_for(IN_USE_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "healthy"


class TestPartiallyQuarantinedPoolWarns:
    """Degraded capacity is visible before it becomes an outage."""

    def test_partial_quarantine_reports_warning(self):
        # Arrange
        status_data = _status_data_for(DEGRADED_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "warning"

    def test_partial_quarantine_issue_is_warning_level(self):
        # Arrange
        status_data = _status_data_for(DEGRADED_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues[0]["level"] == "warning"

    def test_partial_quarantine_issue_names_the_repair_command(self):
        # Arrange
        status_data = _status_data_for(DEGRADED_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert "reconcile_visitor_slots" in issues[0]["message"]


class TestPoolCheckNeverBreaksTheEndpoint:
    """A health check must not 500 the page that reports health."""

    def test_probe_failure_is_reported_not_raised(self):
        # Arrange
        def _boom():
            raise RuntimeError("pool unreachable")

        status_data = {}
        # Act
        check_visitor_pool(status_data, pool_status_fn=_boom)
        # Assert
        assert status_data["visitor_pool"]["health_class"] == "unknown"

    def test_probe_failure_surfaces_as_an_issue(self):
        # Arrange
        def _boom():
            raise RuntimeError("pool unreachable")

        status_data = {}
        check_visitor_pool(status_data, pool_status_fn=_boom)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues[0]["service"] == "Visitor Pool"

    def test_probe_failure_does_not_paint_the_public_dot_red(self):
        # Arrange — unmeasurable is not the same as proven-down
        def _boom():
            raise RuntimeError("pool unreachable")

        status_data = {}
        check_visitor_pool(status_data, pool_status_fn=_boom)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "healthy"


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
