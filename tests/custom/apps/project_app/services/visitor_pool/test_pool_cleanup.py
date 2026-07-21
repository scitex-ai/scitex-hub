#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the stale-slot reaper — cleanup_expired_allocations.

Reproduces and guards the prod 2026-07-09 wedge: zombie ``is_active=True``
rows with a weeks-old ``last_activity`` that no reaper ever freed, so
``get_pool_status`` reported free=0 and every visitor fell back to
readonly-visitor. The reaper must release EVERY expired OR idle slot; a
fresh, genuinely-live allocation must survive.

Real DB via pytest-django ``TestCase`` — no mocks (STX-NM001).
"""

import secrets
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool


def _mk(
    number,
    *,
    is_active=True,
    expires_in_minutes=30,
    last_activity_minutes_ago=None,
    workspace_ready=True,
):
    """Create a VisitorAllocation row with explicit staleness dimensions."""
    now = timezone.now()
    last_activity = (
        None
        if last_activity_minutes_ago is None
        else now - timedelta(minutes=last_activity_minutes_ago)
    )
    return VisitorAllocation.objects.create(
        visitor_number=number,
        session_key=f"sess-{number}",
        allocation_token=secrets.token_hex(16),
        expires_at=now + timedelta(minutes=expires_in_minutes),
        is_active=is_active,
        last_activity=last_activity,
        workspace_ready=workspace_ready,
    )


class TestReaperFreesStaleAllocations(TestCase):
    """cleanup_expired_allocations releases expired AND idle slots."""

    def test_reaper_frees_expired_active_slots(self):
        # Arrange: 3 active rows whose hard expiry is in the past.
        for n in (1, 2, 3):
            _mk(n, expires_in_minutes=-60)
        # Act
        freed = VisitorPool.cleanup_expired_allocations()
        # Assert
        assert freed == 3

    def test_expired_slots_become_inactive_after_reaping(self):
        # Arrange
        alloc = _mk(1, expires_in_minutes=-60)
        # Act
        VisitorPool.cleanup_expired_allocations()
        alloc.refresh_from_db()
        # Assert
        assert alloc.is_active is False

    def test_reaper_frees_idle_slot_with_future_expiry(self):
        # Arrange: the prod zombie — NOT expired (future) but weeks idle.
        _mk(1, expires_in_minutes=30, last_activity_minutes_ago=60 * 24 * 14)
        # Act
        freed = VisitorPool.cleanup_expired_allocations()
        # Assert
        assert freed == 1

    def test_idle_slot_with_future_expiry_becomes_inactive(self):
        # Arrange
        alloc = _mk(
            1, expires_in_minutes=30, last_activity_minutes_ago=60 * 24 * 14
        )
        # Act
        VisitorPool.cleanup_expired_allocations()
        alloc.refresh_from_db()
        # Assert
        assert alloc.is_active is False

    def test_free_rises_to_total_after_reaping_stale_slots(self):
        # Arrange: N stale (idle, future-expiry) active slots — the exact
        # prod shape that wedged the pool at free=0.
        n = min(3, VisitorPool.POOL_SIZE)
        for i in range(1, n + 1):
            _mk(i, expires_in_minutes=30, last_activity_minutes_ago=60 * 24)
        # Act
        VisitorPool.cleanup_expired_allocations()
        status = VisitorPool.get_pool_status()
        # Assert: every slot is reclaimed → the whole pool is free again.
        assert status["free"] == status["total"]

    def test_reaper_returns_zero_when_no_stale_slots(self):
        # Arrange: a single fresh, live allocation.
        _mk(1, expires_in_minutes=30, last_activity_minutes_ago=1)
        # Act
        freed = VisitorPool.cleanup_expired_allocations()
        # Assert
        assert freed == 0

    def test_reaper_does_not_free_fresh_active_slot(self):
        # Arrange
        alloc = _mk(1, expires_in_minutes=30, last_activity_minutes_ago=1)
        # Act
        VisitorPool.cleanup_expired_allocations()
        alloc.refresh_from_db()
        # Assert
        assert alloc.is_active is True


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
