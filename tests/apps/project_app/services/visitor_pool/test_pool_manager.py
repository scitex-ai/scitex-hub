#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for pool_manager: get_pool_status staleness + allocator self-heal.

Two durability guarantees against the prod 2026-07-09 wedge (zombie
``is_active=True`` rows with weeks-old ``last_activity`` that never
expired):

1. ``get_pool_status`` counts a slot as *free* when its allocation is
   expired OR idle — not only when ``is_active=False`` — so a stuck row
   can never report free=0 while the slot is actually reclaimable.
2. ``_try_allocate_slot`` reclaims an idle (not just expired) active slot
   inline, so the pool self-heals from serving traffic even if the
   periodic celery reaper is not running.

Real DB via pytest-django ``TestCase`` — no mocks (STX-NM001).
"""

import secrets
import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.pool_manager import PoolAllocator
from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
    is_allocation_stale,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
)


def _mk(
    number,
    *,
    is_active=True,
    expires_in_minutes=30,
    last_activity_minutes_ago=None,
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


class MockSession(dict):
    """Real dict-backed Django session stand-in (not a unittest mock)."""

    def __init__(self, session_key="test-session-key"):
        super().__init__()
        self._session_key = session_key

    @property
    def session_key(self):
        return self._session_key

    def save(self):
        pass


class TestGetPoolStatusStaleness(TestCase):
    """A stuck-active-but-stale row is reported as free, never wedged."""

    def test_idle_active_row_with_future_expiry_counts_as_free(self):
        # Arrange: the prod zombie — is_active, future expires_at, idle.
        _mk(1, expires_in_minutes=30, last_activity_minutes_ago=60 * 24 * 14)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert: not counted as an occupied/live slot.
        assert status["allocated"] == 0

    def test_idle_active_row_does_not_wedge_free_at_zero(self):
        # Arrange: fill EVERY slot with an idle zombie (the wedge shape).
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i, expires_in_minutes=30, last_activity_minutes_ago=60 * 24)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert: the whole pool is reclaimable → free, never 0.
        assert status["free"] == status["total"]

    def test_expired_active_row_counts_as_free(self):
        # Arrange
        _mk(1, expires_in_minutes=-60)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["free"] == status["total"]

    def test_live_active_row_counts_as_occupied(self):
        # Arrange: one genuinely-live session.
        _mk(1, expires_in_minutes=30, last_activity_minutes_ago=1)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["allocated"] == 1

    def test_live_active_row_reduces_free_by_one(self):
        # Arrange
        _mk(1, expires_in_minutes=30, last_activity_minutes_ago=1)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["free"] == status["total"] - 1

    def test_free_is_never_negative(self):
        # Arrange: more rows than the pool cannot happen (unique
        # visitor_number), but a full pool of live sessions must clamp.
        for i in range(1, VisitorPool.POOL_SIZE + 1):
            _mk(i, expires_in_minutes=30, last_activity_minutes_ago=1)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["free"] >= 0


class TestAllocatorReclaimsIdleSlot(TestCase):
    """The allocator self-heals idle slots without the celery reaper."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            username="visitor-001", defaults={"email": "v001@example.com"}
        )
        Project.objects.get_or_create(
            slug="default-project",
            owner=self.user,
            defaults={"name": "Default Project"},
        )
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        # Slot 1: is_active, workspace_ready, future expiry, but IDLE.
        self.allocation = _mk(
            1,
            is_active=True,
            expires_in_minutes=30,
            last_activity_minutes_ago=60 * 24,
            workspace_ready=True,
        )

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_idle_active_slot_is_released_on_allocation_attempt(self):
        # Arrange
        session = MockSession("new-visitor-session")
        # Act
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        # Assert: the idle slot was reclaimed (released), not left wedged.
        assert self.allocation.is_active is False

    def test_idle_active_slot_is_not_served_the_dirty_request(self):
        # Arrange
        session = MockSession("new-visitor-session")
        # Act: the released slot's workspace is dirty until re-verified.
        project, _ = VisitorPool.allocate_visitor(session)
        # Assert
        assert project is None


class TestAllocationStartsTheIdleClock(TestCase):
    """A slot handed to a visitor must not immediately read as idle.

    Regression for prod 2026-07-14 (every visitor got readonly-visitor).
    ``_try_allocate_slot`` set ``is_active=True`` but never stamped
    ``last_activity``, so the row kept whatever ancient value it already had
    — on prod, days old (and ``allocated_at`` is ``auto_now_add``, so it
    still read February). ``is_allocation_stale()`` was therefore True the
    instant the slot was handed over, and the NEXT request reclaimed it with
    ``reason="idle-lazy"``, flipping ``workspace_ready`` off and queueing a
    wipe. Visitors were evicted seconds after arriving, the pool sat at 0
    allocatable, and everyone fell through to the shared read-only user.

    The idle reclaim itself is correct (see TestAllocatorReclaimsIdleSlot);
    it was starving because nothing ever started the clock it reads.
    """

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            username="visitor-001", defaults={"email": "v001@example.com"}
        )
        self.project, _ = Project.objects.get_or_create(
            slug="default-project",
            owner=self.user,
            defaults={"name": "Default Project"},
        )
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        # Prod's exact resting shape: verified clean and ready, NOT active,
        # carrying a last_activity from days ago (nothing refreshes it).
        self.allocation = _mk(
            1,
            is_active=False,
            expires_in_minutes=-60,
            last_activity_minutes_ago=60 * 24 * 3,
            workspace_ready=True,
        )
        # The synchronous pre-handoff check refuses a slot without the
        # template marker, so give it one or every allocation here is a
        # vacuous None.
        manager = get_project_filesystem_manager(self.user)
        marker = Path(manager.base_path) / self.project.slug / TEMPLATE_MARKER_RELPATH
        marker.mkdir(parents=True, exist_ok=True)
        (marker / "config.yaml").write_text("template: true\n")

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_a_clean_ready_slot_is_actually_handed_out(self):
        # Arrange: guards this class — if handoff fails, the rest is vacuous.
        session = MockSession("visitor-a")
        # Act
        project, _ = VisitorPool.allocate_visitor(session)
        # Assert
        assert project is not None

    def test_allocation_stamps_last_activity(self):
        # Arrange
        session = MockSession("visitor-a")
        # Act
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        # Assert: the idle clock starts at handoff, not days ago.
        assert self.allocation.last_activity > timezone.now() - timedelta(minutes=1)

    def test_freshly_allocated_slot_is_not_stale(self):
        # Arrange
        session = MockSession("visitor-a")
        # Act
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        # Assert: THE bug — a just-handed-out slot must never read as idle.
        assert is_allocation_stale(self.allocation) is False

    def test_the_next_request_does_not_evict_the_live_visitor(self):
        # Arrange: visitor A takes the slot.
        VisitorPool.allocate_visitor(MockSession("visitor-a"))
        # Act: visitor B arrives one request later and scans the pool.
        VisitorPool.allocate_visitor(MockSession("visitor-b"))
        self.allocation.refresh_from_db()
        # Assert: A still holds it; B must not reclaim it as "idle".
        assert self.allocation.is_active is True

    def test_the_next_request_does_not_drain_the_slot_from_the_pool(self):
        # Arrange
        VisitorPool.allocate_visitor(MockSession("visitor-a"))
        # Act
        VisitorPool.allocate_visitor(MockSession("visitor-b"))
        self.allocation.refresh_from_db()
        # Assert: the bogus eviction also flipped workspace_ready off, which
        # is what drained the pool to 0 allocatable and read-only'd everyone.
        assert self.allocation.workspace_ready is True


class TestProbationLease(TestCase):
    """A slot is provisional until a heartbeat proves a real browser.

    Regression for prod 2026-07-14 (second half of the read-only saga):
    allocation used to grant the full 1-hour session to ANY cookie-less
    request. A crawler walked the site and squatted all 16 slots
    sequentially in ~10 minutes — none of those sessions ever hit
    /api/visitor/heartbeat/ (1 hit in 5000 nginx lines) — so the pool sat
    at 0 allocatable and every human got readonly-visitor.

    Now allocation grants only PROBATION_SECONDS; the first heartbeat
    (fired ~1s after page load by visitor-heartbeat.ts) promotes to the
    full session, and later beats keep extending it. A client that never
    executes JS never beats, so its lease lapses and the slot returns to
    the pool in minutes instead of an hour.
    """

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            username="visitor-001", defaults={"email": "v001@example.com"}
        )
        self.project, _ = Project.objects.get_or_create(
            slug="default-project",
            owner=self.user,
            defaults={"name": "Default Project"},
        )
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _mk(
            1,
            is_active=False,
            expires_in_minutes=-60,
            last_activity_minutes_ago=60 * 24 * 3,
            workspace_ready=True,
        )
        manager = get_project_filesystem_manager(self.user)
        marker = Path(manager.base_path) / self.project.slug / TEMPLATE_MARKER_RELPATH
        marker.mkdir(parents=True, exist_ok=True)
        (marker / "config.yaml").write_text("template: true\n")

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def _allocate(self):
        VisitorPool.allocate_visitor(MockSession("visitor-a"))
        self.allocation.refresh_from_db()

    def test_allocation_grants_probation_not_the_full_session(self):
        # Arrange
        session = MockSession("visitor-a")
        # Act
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        lease = (self.allocation.expires_at - timezone.now()).total_seconds()
        # Assert: minutes, not the 1-hour session a crawler used to squat.
        assert lease <= PoolAllocator.PROBATION_SECONDS + 30

    def test_allocation_lease_is_in_the_future(self):
        # Arrange
        session = MockSession("visitor-a")
        # Act
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        # Assert: probation is a real window, not an instant expiry.
        assert self.allocation.expires_at > timezone.now()

    def test_unbeaten_lease_is_stale_after_probation(self):
        # Arrange: allocated, never heartbeats (a crawler).
        self._allocate()
        after_probation = timezone.now() + timedelta(
            seconds=PoolAllocator.PROBATION_SECONDS + 60
        )
        # Act
        stale = is_allocation_stale(self.allocation, now=after_probation)
        # Assert: reclaimable minutes after the squat, not an hour.
        assert stale is True

    def test_heartbeat_within_probation_keeps_the_slot(self):
        # Arrange: allocated, then the browser's first heartbeat lands.
        self._allocate()
        VisitorPool.extend_session_on_activity(self.allocation)
        after_probation = timezone.now() + timedelta(
            seconds=PoolAllocator.PROBATION_SECONDS + 60
        )
        # Act
        stale = is_allocation_stale(self.allocation, now=after_probation)
        # Assert: a confirmed browser is NOT reclaimed at probation end.
        assert stale is False

    def test_first_heartbeat_promotes_to_the_full_session(self):
        # Arrange
        self._allocate()
        # Act
        VisitorPool.extend_session_on_activity(self.allocation)
        runway = (self.allocation.expires_at - timezone.now()).total_seconds()
        # Assert: promoted to ~SESSION_LIFETIME_HOURS of runway.
        assert runway >= (PoolAllocator.SESSION_LIFETIME_HOURS * 3600) - 60

    def test_heartbeat_never_shortens_a_longer_lease(self):
        # Arrange: lease already longer than one full session.
        self._allocate()
        far = timezone.now() + timedelta(hours=2)
        self.allocation.expires_at = far
        self.allocation.save(update_fields=["expires_at"])
        # Act
        VisitorPool.extend_session_on_activity(self.allocation)
        # Assert: max() semantics — extension is one-way.
        assert self.allocation.expires_at >= far

    def test_heartbeat_stamps_last_activity(self):
        # Arrange
        self._allocate()
        self.allocation.last_activity = timezone.now() - timedelta(minutes=20)
        self.allocation.save(update_fields=["last_activity"])
        # Act
        VisitorPool.extend_session_on_activity(self.allocation)
        # Assert: the idle clock restarts on every beat.
        assert self.allocation.last_activity > timezone.now() - timedelta(minutes=1)

    def test_allocation_stamps_allocated_at(self):
        # Arrange: the row predates this visitor by days (rows are reused;
        # auto_now_add meant prod rows still read February).
        VisitorAllocation.objects.filter(pk=self.allocation.pk).update(
            allocated_at=timezone.now() - timedelta(days=90)
        )
        # Act
        self._allocate()
        # Assert: allocated_at records THIS handoff, not row creation.
        assert self.allocation.allocated_at > timezone.now() - timedelta(minutes=1)


class IdleTimeoutConstantAliasTest(TestCase):
    """PoolAllocator.IDLE_TIMEOUT_MINUTES aliases the reaper's constant.

    User-facing copy (visitor banner) quotes the class attr, while the
    idle reaper enforces slot_lifecycle.IDLE_TIMEOUT_MINUTES — the two
    must be the same object so the promise can never drift from the
    eviction actually enforced (card hub-visitor-banner-identity-and-
    lifetime).
    """

    def test_pool_allocator_idle_timeout_aliases_slot_lifecycle(self):
        # Arrange
        from apps.infra.project_app.services.visitor_pool import slot_lifecycle

        # Act
        quoted = PoolAllocator.IDLE_TIMEOUT_MINUTES
        # Assert
        assert quoted == slot_lifecycle.IDLE_TIMEOUT_MINUTES


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
