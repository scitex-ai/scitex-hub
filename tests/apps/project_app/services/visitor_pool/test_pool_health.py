#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The capacity partition, measured against a real DB.

These are the tests that stop the DEFINITION drifting from the ALLOCATOR
again. Every visitor-pool incident in this repo's history is one number
meaning three things: ``free`` (total minus occupied) claimed spare capacity
while every visitor was downgraded (prod 2026-07-30); a "workspace is clean"
count read as availability while 16 of 16 slots were held (prod 2026-08-16
15:55Z). Both numbers were correct. Neither answered "can the NEXT visitor get
a real slot?".

``allocatable`` answers exactly that, with exactly the predicate
``PoolAllocator._try_allocate_slot`` serves::

    quarantined=False AND is_active=False AND workspace_ready=True

Pinned here row-by-row so a future edit to either side fails loudly.

Real DB via pytest-django ``TestCase`` — no mocks (STX-NM001).
"""

import secrets
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.pool_manager import PoolAllocator
from apps.infra.public_app.views.status.visitor_pool_health import (
    classify_visitor_pool,
)

# Pool size is read from the environment (``SCITEX_HUB_VISITOR_POOL_SIZE``,
# default 4), so a test that hardcodes 16 passes on prod's shape and fails on
# the default. Where the SIZE is part of what is under test, these call
# ``PoolAllocator.get_pool_status(n)`` with an explicit n — a real function
# with a real argument, not a patched global.
PROD_POOL_SIZE = 16


def _mk(
    number,
    *,
    is_active=True,
    expires_in_minutes=30,
    last_activity_minutes_ago=1,
    workspace_ready=True,
    quarantined=False,
):
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
        quarantined=quarantined,
    )


def _buckets_sum(status: dict) -> int:
    return (
        status["allocatable"]
        + status["live"]
        + status["reclaimable"]
        + status["resetting"]
        + status["quarantined"]
        + status["missing"]
    )


class TestHeldSlotsAreNotAllocatable(TestCase):
    """A clean workspace under a LIVE session is not spare capacity."""

    def test_live_clean_slot_is_not_allocatable(self):
        # Arrange — is_active, future expiry, recent beat, workspace clean
        _mk(1)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["allocatable"] == 0

    def test_live_clean_slot_counts_as_live(self):
        # Arrange
        _mk(1)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["live"] == 1

    def test_whole_pool_held_reports_zero_allocatable(self):
        # Arrange — THE CASE THAT MATTERS, built from real rows: every slot
        # held by a live session, workspaces clean, nothing quarantined.
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert (status["allocatable"], status["quarantined"]) == (0, 0)

    def test_whole_pool_held_is_classified_red(self):
        # Arrange
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i)
        # Act
        entry = classify_visitor_pool(VisitorPool.get_pool_status())
        # Assert — end-to-end: ORM count -> health entry -> red
        assert entry["status"] == "error"

    def test_whole_pool_held_names_saturation_not_the_reconcile(self):
        # Arrange
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i)
        # Act
        entry = classify_visitor_pool(VisitorPool.get_pool_status())
        # Assert — a --repair-only here is a no-op that reads as a real fix
        assert entry["cause"] == "saturated"


class TestReclaimableIsNotAllocatable(TestCase):
    """Capacity that returns LATER is not capacity the next request gets."""

    def test_expired_active_slot_is_reclaimable_not_allocatable(self):
        # Arrange — probation lapsed, workspace still clean
        _mk(1, expires_in_minutes=-5)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert (status["reclaimable"], status["allocatable"]) == (1, 0)

    def test_idle_active_slot_is_reclaimable_not_live(self):
        # Arrange — future expiry but the visitor walked away (the zombie)
        _mk(1, expires_in_minutes=30, last_activity_minutes_ago=31)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert (status["reclaimable"], status["live"]) == (1, 0)

    def test_reclaimable_slot_still_reports_free_for_back_compat(self):
        # Arrange — ``free`` keeps its old meaning; three consumers read it
        _mk(1, expires_in_minutes=-5)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["free"] == status["total"]


class TestResettingAndQuarantinedBuckets(TestCase):
    """Released-but-unwiped and failed-verify are different faults."""

    def test_released_unwiped_slot_counts_as_resetting(self):
        # Arrange — release_slot sets workspace_ready=False unconditionally
        _mk(1, is_active=False, workspace_ready=False)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert (status["resetting"], status["allocatable"]) == (1, 0)

    def test_quarantined_slot_is_not_allocatable(self):
        # Arrange
        _mk(1, is_active=False, workspace_ready=True, quarantined=True)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert (status["quarantined"], status["allocatable"]) == (1, 0)

    def test_clean_idle_slot_is_allocatable(self):
        # Arrange — the one shape the allocator actually serves
        _mk(1, is_active=False, workspace_ready=True)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["allocatable"] == 1


class TestPartitionInvariant(TestCase):
    """The buckets must sum to the pool size, always."""

    def test_empty_pool_is_all_missing(self):
        # Arrange — pool size configured, no rows provisioned
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["missing"] == VisitorPool.POOL_SIZE

    def test_partly_provisioned_pool_sums_to_total(self):
        # Arrange — 3 rows for a pool of POOL_SIZE
        for i in range(1, 4):
            _mk(i)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert _buckets_sum(status) == status["total"]

    def test_mixed_pool_sums_to_total(self):
        # Arrange — one of every bucket, plus 3 unprovisioned slot numbers
        _mk(1)
        _mk(2, expires_in_minutes=-5)
        _mk(3, is_active=False, workspace_ready=False)
        _mk(4, is_active=False, quarantined=True)
        _mk(5, is_active=False, workspace_ready=True)
        # Act
        status = PoolAllocator.get_pool_status(8)
        # Assert
        assert _buckets_sum(status) == status["total"]

    def test_mixed_pool_counts_unprovisioned_slots_as_missing(self):
        # Arrange — 5 rows for an 8-slot pool
        for i in range(1, 6):
            _mk(i, is_active=False, workspace_ready=True)
        # Act
        status = PoolAllocator.get_pool_status(8)
        # Assert — previously these appeared in NO bucket at all
        assert status["missing"] == 3

    def test_rows_beyond_pool_size_are_not_counted(self):
        # Arrange — the shrunk-pool shape: a row the allocator can never reach
        # because it only ever walks range(1, pool_size + 1).
        _mk(VisitorPool.POOL_SIZE + 1, is_active=False, workspace_ready=True)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert — it must not inflate allocatable with unreachable capacity
        assert status["allocatable"] == 0


class TestMeasuredProdSnapshot(TestCase):
    """Rebuild 2026-08-16 15:55:08Z row-for-row and re-read it.

    Prod runs a 16-slot pool, so this asks ``PoolAllocator.get_pool_status``
    for 16 explicitly rather than depending on the environment's
    ``SCITEX_HUB_VISITOR_POOL_SIZE`` (default 4).
    """

    def _build_snapshot(self):
        """The measured row census, reproduced exactly.

            active_live=12  active_expired=1  inactive=3
            limbo(not clean, not quarantined)=4
            workspace-clean=12   quarantined=0   ALLOCATABLE=1

        Those five numbers pin each other: 12 clean of 16 with 4 in limbo,
        and only ONE of the clean rows also inactive. That single row is the
        entire capacity of the pool at 15:55:08Z.
        """
        for i in range(1, 12):  # 11 live sessions on clean workspaces
            _mk(i)
        _mk(12, workspace_ready=False)  # 12th live session, mid-limbo
        _mk(13, expires_in_minutes=-1, workspace_ready=False)  # probation lapsed
        _mk(14, is_active=False, workspace_ready=False)  # awaiting wipe
        _mk(15, is_active=False, workspace_ready=False)  # awaiting wipe
        _mk(16, is_active=False, workspace_ready=True)  # the ONE allocatable

    def test_snapshot_reports_one_allocatable(self):
        # Arrange
        self._build_snapshot()
        # Act
        status = PoolAllocator.get_pool_status(PROD_POOL_SIZE)
        # Assert — not 12 ("clean"), not 5 ("free"): ONE
        assert status["allocatable"] == 1

    def test_snapshot_reports_twelve_workspace_clean_rows(self):
        # Arrange — pins the premise: "clean" really was 12 that day
        self._build_snapshot()
        # Act
        clean = VisitorAllocation.objects.filter(
            quarantined=False, workspace_ready=True
        ).count()
        # Assert
        assert clean == 12

    def test_snapshot_reports_zero_quarantined(self):
        # Arrange
        self._build_snapshot()
        # Act
        status = PoolAllocator.get_pool_status(PROD_POOL_SIZE)
        # Assert — which is why #628's quarantined>0 branch never fired
        assert status["quarantined"] == 0

    def test_snapshot_buckets_sum_to_the_pool_size(self):
        # Arrange
        self._build_snapshot()
        # Act
        status = PoolAllocator.get_pool_status(PROD_POOL_SIZE)
        # Assert — 12 live + 1 reclaimable + 2 resetting + 1 allocatable
        assert _buckets_sum(status) == PROD_POOL_SIZE

    def test_snapshot_is_not_reported_healthy(self):
        # Arrange
        self._build_snapshot()
        # Act
        entry = classify_visitor_pool(PoolAllocator.get_pool_status(PROD_POOL_SIZE))
        # Assert — one arrival from the outage a real visitor already met
        assert entry["is_healthy"] is False


class TestWholeProdPoolHeld(TestCase):
    """A 16-slot pool with every slot held is RED, not green."""

    def test_sixteen_held_slots_report_zero_allocatable(self):
        # Arrange — 16 live sessions, clean workspaces, none quarantined
        for i in range(1, PROD_POOL_SIZE + 1):
            _mk(i)
        # Act
        status = PoolAllocator.get_pool_status(PROD_POOL_SIZE)
        # Assert
        assert status["allocatable"] == 0

    def test_sixteen_held_slots_are_classified_red(self):
        # Arrange
        for i in range(1, PROD_POOL_SIZE + 1):
            _mk(i)
        # Act
        entry = classify_visitor_pool(PoolAllocator.get_pool_status(PROD_POOL_SIZE))
        # Assert — end-to-end: ORM count -> health entry -> red
        assert entry["status"] == "error"

    def test_sixteen_held_slots_name_saturation(self):
        # Arrange
        for i in range(1, PROD_POOL_SIZE + 1):
            _mk(i)
        # Act
        entry = classify_visitor_pool(PoolAllocator.get_pool_status(PROD_POOL_SIZE))
        # Assert — a --repair-only here is a no-op that reads as a real fix
        assert entry["cause"] == "saturated"


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
