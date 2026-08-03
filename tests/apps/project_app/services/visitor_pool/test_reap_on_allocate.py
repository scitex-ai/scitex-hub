#!/usr/bin/env python3
"""Allocation must reclaim expired leases itself, not wait for the periodic beat.

Card hub-visitor-pool-ua-gate-admits-crawlers-20260803.

THE BUG, measured on prod 2026-08-03 over a 57-minute passive sample.

A fresh allocation is a PROBATION_SECONDS (120s) provisional lease — a crawler
that never runs JS simply expires out of it. But
`cleanup-expired-visitor-allocations` fires only every 300s (confirmed from the
deployed beat scheduler's own log: 24 firings in 2h, exactly 300s apart, while
control tasks fired 120x). So an expired slot stayed dead-but-unavailable for up
to 120 + 300 + 20(reclean) = 440s.

Across 16 slots that is a capacity of one allocation per 27.5s, against a
measured demand of one per 33.1s. A ~20% margin under a bursty arrival process
does not fail steadily, it fails in clusters — exactly what was observed:

    13:07:15  allocated=16 free=0  ready=0            <- pool 100% saturated
    13:09:15  allocated=1  free=15 expired=15 ready=0 <- 15 dead, none reclaimed
    13:09:54  beat: Sending due task cleanup-expired-visitor-allocations
    13:10:35  allocated=2  free=14 ready=5            <- recovered

`ready` was 0 in 16% of samples, i.e. roughly one arrival in six was demoted to
readonly-visitor at the top of the revenue funnel.

WHAT THESE TESTS ASSERT, AND WHY NOT THE OBVIOUS THING.

They assert the SLOT gets reclaimed, NOT that the triggering request succeeds.
`release_slot` sets workspace_ready=False and defers an async wipe+verify via
transaction.on_commit; that reset takes 17-21s, so the request that triggers the
reap still gets readonly. Asserting otherwise would produce a test that cannot
pass, and would tempt an implementer to "fix" it by making the reset synchronous
— putting a 20s wipe on the request path, which is far worse than the bug.

No mocks — real rows, real allocator. One assertion per test (STX-TQ007).
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.visitor_pool.pool_manager import PoolAllocator

POOL_SIZE = 4


class ReapOnAllocateTest(TestCase):
    """Allocation reclaims expired leases in-line rather than deferring to beat."""

    def _make_slot(self, num, *, expired, ready=True):
        """One pool slot with its visitor user and default-project.

        The user/project are REQUIRED: _try_allocate_slot bails out (and logs
        "user/project not found") before it ever consults the readiness gate, so
        a slot without them would make every test here pass for the wrong reason.
        """
        user = User.objects.create_user(username=f"visitor-{num:03d}")
        Project.objects.create(slug="default-project", name="My Project", owner=user)
        now = timezone.now()
        return VisitorAllocation.objects.create(
            visitor_number=num,
            allocation_token=f"tok-{num:03d}",
            allocated_at=now - timedelta(hours=2),
            expires_at=(now - timedelta(minutes=5)) if expired else (now + timedelta(minutes=30)),
            last_activity=now - timedelta(hours=2) if expired else now,
            is_active=True,
            workspace_ready=ready,
        )

    def test_expired_leases_are_reclaimed_during_allocation(self):
        """THE REGRESSION. Pre-fix this leaves all slots is_active=True."""
        # Arrange — every slot held by an expired lease, none reclaimed yet
        for n in range(1, POOL_SIZE + 1):
            self._make_slot(n, expired=True)
        # Act
        PoolAllocator.allocate_visitor(self.client.session, POOL_SIZE)
        # Assert
        assert not VisitorAllocation.objects.filter(is_active=True).exists()

    def test_reclaimed_slots_are_marked_not_ready_pending_wipe(self):
        """A reclaimed slot must NOT be handed out before its wipe verifies."""
        # Arrange
        for n in range(1, POOL_SIZE + 1):
            self._make_slot(n, expired=True)
        # Act
        PoolAllocator.allocate_visitor(self.client.session, POOL_SIZE)
        # Assert
        assert not VisitorAllocation.objects.filter(workspace_ready=True).exists()

    def test_live_leases_are_not_reclaimed(self):
        """CONTROL. Without this, a reaper that frees EVERYTHING also passes.

        This is the assertion that makes the two above meaningful: a broken
        implementation that released every slot unconditionally would satisfy
        them both and would evict live visitors mid-session.
        """
        # Arrange — every slot genuinely busy, nothing expired
        for n in range(1, POOL_SIZE + 1):
            self._make_slot(n, expired=False)
        # Act
        PoolAllocator.allocate_visitor(self.client.session, POOL_SIZE)
        # Assert
        assert VisitorAllocation.objects.filter(is_active=True).count() == POOL_SIZE

    def test_a_ready_slot_is_still_allocated_without_any_reaping(self):
        """CONTROL. The happy path must not regress, and must not reap.

        Guards the ordinary case: when a clean slot exists the allocator returns
        it on the FIRST pass, so the reap branch is never entered.
        """
        # Arrange — slot 1 free and verified clean, the rest busy
        free = self._make_slot(1, expired=False)
        free.is_active = False
        free.save(update_fields=["is_active"])
        for n in range(2, POOL_SIZE + 1):
            self._make_slot(n, expired=False)
        # Act
        project, user = PoolAllocator.allocate_visitor(self.client.session, POOL_SIZE)
        # Assert
        assert project is not None

    def test_nothing_reclaimable_does_not_loop(self):
        """No expired rows => the second scan is skipped, not run pointlessly.

        Asserted through the outcome the caller sees rather than by counting
        passes: with every slot busy-and-live the allocator must still return
        (None, None) so the readonly fallback records its reason.
        """
        # Arrange
        for n in range(1, POOL_SIZE + 1):
            self._make_slot(n, expired=False)
        # Act
        project, _user = PoolAllocator.allocate_visitor(self.client.session, POOL_SIZE)
        # Assert
        assert project is None
