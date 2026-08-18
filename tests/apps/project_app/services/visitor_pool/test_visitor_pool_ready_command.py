#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The deploy gate keys on ALLOCATABLE and names the repair that fits.

``visitor_pool_ready`` is step 7d of ``scripts/deploy/rebuild.sh``: the
assertion that turns "the re-clean was dispatched" into "a visitor can
actually get a slot". Two things about it were too narrow.

1. It passed on ``ready >= 1`` and said nothing more. On 2026-08-16 15:55Z
   prod sat at ONE allocatable slot of 16 — passing, and one arrival from the
   outage, because a consumed slot does not return for tens of minutes.

2. Its failure text hardcoded ``reconcile_visitor_slots --repair-only`` for
   EVERY failure. That command re-cleans only ``quarantined=True`` rows, so
   against a saturated pool it is a no-op that reads to the operator as "I ran
   the documented fix and nothing changed" — worse than naming no repair.

``--min-ready`` stays at 1 as the FAIL threshold (a deploy that lands one slot
is not a failed deploy); thin headroom is now reported by ``--warn-below``,
which is loud and still exits 0.

Real DB via pytest-django ``TestCase`` — no mocks (STX-NM001). The command
reads the pool through the real ORM, so the rows below are the whole fixture.
"""

import secrets
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool


def _mk(number, *, is_active=True, workspace_ready=True, quarantined=False):
    now = timezone.now()
    return VisitorAllocation.objects.create(
        visitor_number=number,
        session_key=f"sess-{number}",
        allocation_token=secrets.token_hex(16),
        expires_at=now + timedelta(minutes=30),
        is_active=is_active,
        last_activity=now - timedelta(minutes=1),
        workspace_ready=workspace_ready,
        quarantined=quarantined,
    )


def _run(**kwargs) -> str:
    out = StringIO()
    call_command("visitor_pool_ready", stdout=out, **kwargs)
    return out.getvalue()


def _failure_text(**kwargs) -> str:
    """The gate's failure message, or "" if it unexpectedly passed.

    Keeps each test to ONE assertion (STX-TQ007): the raise itself is asserted
    separately from the wording it carries.
    """
    try:
        _run(**kwargs)
    except CommandError as exc:
        return str(exc)
    return ""


class TestSaturatedPoolFailsWithTheCapacityRepair(TestCase):
    """Every slot held: the reconcile would do nothing, so do not name it."""

    def setUp(self):
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i)

    def test_saturated_pool_fails_the_gate(self):
        # Arrange — 16 live sessions, 0 quarantined, 0 allocatable
        expected = CommandError
        # Act
        # Assert
        with pytest.raises(expected):
            _run()

    def test_saturated_failure_names_the_capacity_knob(self):
        # Arrange — see setUp
        # Act
        message = _failure_text()
        # Assert
        assert "SCITEX_HUB_VISITOR_POOL_SIZE" in message

    def test_saturated_failure_does_not_offer_the_repair_only_no_op(self):
        # Arrange — see setUp
        # Act
        message = _failure_text()
        # Assert — the negative assertion IS the test
        assert "--repair-only" not in message

    def test_saturated_failure_reports_the_partition(self):
        # Arrange — see setUp
        # Act
        message = _failure_text()
        # Assert — the operator must see WHY, not just THAT
        assert "held by live sessions" in message


class TestQuarantinedPoolStillNamesRepairOnly(TestCase):
    """#628's case must not regress."""

    def setUp(self):
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i, is_active=False, quarantined=True)

    def test_quarantined_pool_fails_the_gate(self):
        # Arrange — the 2026-08-16 14:49Z outage shape
        expected = CommandError
        # Act
        # Assert
        with pytest.raises(expected):
            _run()

    def test_quarantined_failure_names_the_safe_repair(self):
        # Arrange — see setUp
        # Act
        message = _failure_text()
        # Assert
        assert "--repair-only" in message


class TestThinHeadroomPassesLoudly(TestCase):
    """Passing and being healthy are different questions."""

    def _fill_with_one_slot_left(self):
        """The measured 15:55Z headroom: ONE allocatable, the rest held."""
        _mk(1, is_active=False, workspace_ready=True)
        for i in range(2, VisitorPool.POOL_SIZE + 1):
            _mk(i)

    def test_one_allocatable_slot_still_passes(self):
        # Arrange
        self._fill_with_one_slot_left()
        # Act — a deploy that lands one slot is not a failed deploy
        output = _run()
        # Assert
        assert "WARNING" in output

    def test_one_allocatable_slot_names_its_cause(self):
        # Arrange
        self._fill_with_one_slot_left()
        # Act
        output = _run()
        # Assert
        assert "saturated" in output

    def test_min_ready_above_headroom_still_fails(self):
        # Arrange
        self._fill_with_one_slot_left()
        expected = CommandError
        # Act
        # Assert — the fail threshold is still configurable
        with pytest.raises(expected):
            _run(min_ready=4)


class TestHealthyPoolPassesQuietly(TestCase):
    """A gate that never passes gets disabled within a week."""

    def _fill_with_headroom(self):
        """One visitor working, every other slot allocatable.

        Written relative to ``POOL_SIZE`` on purpose: it is read from
        ``SCITEX_HUB_VISITOR_POOL_SIZE`` (default 4, prod 16), so a fixture
        that hardcoded prod's shape would warn instead of passing on the
        default and this class would test the opposite of its name.
        """
        _mk(1)
        for i in range(2, VisitorPool.POOL_SIZE + 1):
            _mk(i, is_active=False, workspace_ready=True)

    def test_pool_with_headroom_prints_ok(self):
        # Arrange
        self._fill_with_headroom()
        # Act
        output = _run()
        # Assert
        assert "OK:" in output

    def test_pool_with_headroom_does_not_warn(self):
        # Arrange
        self._fill_with_headroom()
        # Act
        output = _run()
        # Assert
        assert "WARNING" not in output

    def test_pool_with_headroom_reports_allocatable_not_free(self):
        # Arrange
        self._fill_with_headroom()
        # Act
        output = _run()
        # Assert
        assert "allocatable" in output


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
