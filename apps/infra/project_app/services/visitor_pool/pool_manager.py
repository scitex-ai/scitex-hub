"""
Visitor Pool Allocation and Deallocation Management

Handles allocation of visitor slots from the pre-allocated pool and
deallocation when sessions expire or users sign up.

Security model (visitor-slot isolation audit 2026-07-07): the wipe
happens on RELEASE, asynchronously; allocation only ever hands out
slots whose workspace has been wiped + VERIFIED clean since the last
visitor (``workspace_ready=True``, ``quarantined=False``) and which
pass a synchronous template-marker check. A slot in any other state is
refused — with no ready slot the caller falls back to the shared
readonly-visitor (reason flag in the session). This holds even with
Celery down: unreset slots simply stay out of circulation.
"""

import logging
import secrets
from datetime import timedelta
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation

from .session_role import (
    READONLY_REASON_NO_READY_SLOT,
    READONLY_REASON_POOL_FULL,
    SESSION_KEY_READONLY_REASON,
)
from .slot_lifecycle import (
    IDLE_TIMEOUT_MINUTES,
    is_allocation_stale,
    quarantine_slot,
    release_slot,
    stale_allocation_q,
)

logger = logging.getLogger(__name__)


class PoolAllocator:
    """Manages allocation of visitor slots from the pool."""

    VISITOR_USER_PREFIX = "visitor-"
    POOL_SIZE = None  # Will be set by VisitorPool
    SESSION_LIFETIME_HOURS = 1  # Base session time (extended on activity)
    SESSION_EXTENSION_MINUTES = 30  # Extend by this much on activity
    # Release slot if idle longer than this. Aliases the operative reaper
    # constant (slot_lifecycle — same pattern as PoolCleanup) so anything
    # quoting this class attr (e.g. the visitor banner) can never drift
    # from the eviction behavior actually enforced.
    IDLE_TIMEOUT_MINUTES = IDLE_TIMEOUT_MINUTES
    # Probation: a fresh allocation is a SHORT provisional lease, promoted
    # to the full session by the first heartbeat (extend_session_on_activity).
    # The heartbeat client fires within ~1s of page load, so any JS-executing
    # browser confirms comfortably inside this window — while a plain HTTP
    # client (crawler) never does and simply expires. Without this, every
    # cookie-less bot request held a slot for the full session: on prod
    # 2026-07-14 a crawler walked the site and squatted all 16 slots
    # (sequentially, ~10 min; 1 heartbeat in 5000 nginx lines), so humans
    # got readonly-visitor while the pool was "healthy". Wide enough for a
    # slow phone on a heavy page; a JS-disabled human falls back to
    # readonly-visitor, unchanged from before.
    PROBATION_SECONDS = 120
    SESSION_KEY_PROJECT_ID = "visitor_project_id"
    SESSION_KEY_VISITOR_ID = "visitor_user_id"
    SESSION_KEY_ALLOCATION_TOKEN = "visitor_allocation_token"
    # Canonical key + codes live in session_role (single source of truth
    # for the reason model); re-exposed here for existing callers/tests.
    SESSION_KEY_READONLY_REASON = SESSION_KEY_READONLY_REASON

    @classmethod
    def _check_table_exists(cls) -> bool:
        """Check if VisitorAllocation table exists.

        Uses Django's database-agnostic introspection so the check works
        across SQLite (test/CI), PostgreSQL, and MySQL alike. The previous
        implementation queried ``information_schema.tables`` directly, which
        does not exist on SQLite and silently returned False there, wrongly
        triggering the DemoProjectPool fallback.
        """
        from django.db import connection

        table_name = VisitorAllocation._meta.db_table
        return table_name in connection.introspection.table_names()

    @classmethod
    @transaction.atomic
    def allocate_visitor(
        cls, session, pool_size: int
    ) -> Tuple[Optional[Project], Optional[User]]:
        """
        Allocate a free visitor slot to the session.

        Uses database locking to prevent race conditions.
        Falls back to DemoProjectPool if VisitorAllocation table not created yet.

        Args:
            session: Django session object
            pool_size: Size of the visitor pool

        Returns:
            tuple: (Project, User) or (None, None) if pool exhausted
        """
        # Check if VisitorAllocation table exists
        if not cls._check_table_exists():
            logger.warning(
                "[VisitorPool] VisitorAllocation table not found, using DemoProjectPool fallback"
            )
            from apps.infra.project_app.services.demo_project_pool import (
                DemoProjectPool,
            )

            project, created = DemoProjectPool.get_or_create_demo_project(session)
            return project, project.owner if project else None

        # Check if session already has allocation
        existing_token = session.get(cls.SESSION_KEY_ALLOCATION_TOKEN)
        if existing_token:
            result = cls._reuse_allocation(existing_token, session)
            if result[0] is not None:
                return result

        # Find a free visitor slot. Two passes at most: if the first finds
        # nothing, reclaim expired leases and look again rather than degrading
        # this visitor while dead slots sit waiting for the periodic beat.
        #
        # WHY (measured on prod 2026-08-03, card
        # hub-visitor-pool-ua-gate-admits-crawlers-20260803): a fresh allocation
        # is a PROBATION_SECONDS (120s) provisional lease, but
        # `cleanup-expired-visitor-allocations` fires only every 300s. An expired
        # slot therefore stayed dead-but-unavailable for up to 120+300+20 = 440s
        # (one per 27.5s across 16 slots), against a measured demand of one
        # allocation per 33.1s over a 57-minute window. A ~20% margin under a
        # bursty arrival process does not fail steadily — it fails in bursts,
        # which is what was observed: the pool hit 16/16 four times and `ready`
        # was 0 in 16% of samples, so roughly one arrival in six was demoted to
        # readonly. Reaping here deletes the 300s term (120+0+20 = 140s, one per
        # 8.8s), giving ~3.8x headroom over measured demand.
        #
        # This does NOT rescue the CURRENT request, and that is by design.
        # `release_slot` sets workspace_ready=False and defers an async
        # wipe+verify via transaction.on_commit; that reset takes 17-21s, so the
        # second pass below will usually still find nothing and this visitor
        # still gets readonly. The benefit accrues to the arrivals that follow.
        # Do NOT "fix" that by making the reset synchronous — it would put a 20s
        # wipe on the request path, which is far worse than a readonly session.
        #
        # Reuses PoolCleanup instead of re-deriving the staleness predicate: it
        # shares `stale_allocation_q` with get_pool_status and the allocator, and
        # that shared predicate is what stopped the 2026-07-09 drift where a row
        # was "free" to one reader and "busy" to another.
        for reap_pass in (False, True):
            if reap_pass:
                from .pool_cleanup import PoolCleanup

                freed = PoolCleanup.cleanup_expired_allocations()
                if not freed:
                    # Nothing was reclaimable, so a second scan would re-read the
                    # identical rows. Stop rather than pay a pointless pass.
                    break
                logger.info(
                    f"[VisitorPool] Reaped {freed} expired slot(s) on demand "
                    f"rather than waiting up to 300s for the periodic cleanup; "
                    f"rescanning"
                )
            for i in range(1, pool_size + 1):
                result = cls._try_allocate_slot(i, session, pool_size)
                if result[0] is not None:
                    return result

        # No slot served. Distinguish "all busy" from "free slots exist
        # but none is verified clean yet" so the readonly-visitor
        # fallback can fail loud with the right reason.
        busy = VisitorAllocation.objects.filter(
            is_active=True, expires_at__gt=timezone.now()
        ).count()
        if busy >= pool_size:
            reason = READONLY_REASON_POOL_FULL
            logger.warning(
                f"[VisitorPool] Pool exhausted - all {pool_size} slots in use"
            )
        else:
            reason = READONLY_REASON_NO_READY_SLOT
            logger.warning(
                f"[VisitorPool] No verified-clean slot available "
                f"({busy}/{pool_size} busy; rest awaiting reset or quarantined) "
                f"- falling back to readonly-visitor"
            )
        session[cls.SESSION_KEY_READONLY_REASON] = reason
        session.save()
        return None, None

    @classmethod
    def _reuse_allocation(
        cls, token: str, session
    ) -> Tuple[Optional[Project], Optional[User]]:
        """Reuse existing allocation if still valid."""
        try:
            allocation = VisitorAllocation.objects.get(
                allocation_token=token,
                is_active=True,
                expires_at__gt=timezone.now(),
            )
            visitor_num = allocation.visitor_number
            user = User.objects.get(
                username=f"{cls.VISITOR_USER_PREFIX}{visitor_num:03d}"
            )
            project = Project.objects.get(slug="default-project", owner=user)
            logger.info(f"[VisitorPool] Reusing allocation: visitor-{visitor_num:03d}")
            return project, user
        except (
            VisitorAllocation.DoesNotExist,
            User.DoesNotExist,
            Project.DoesNotExist,
        ):
            logger.warning(
                "[VisitorPool] Invalid allocation token, clearing session and reallocating"
            )
            # Clear stale session data before reallocating
            session.pop(cls.SESSION_KEY_PROJECT_ID, None)
            session.pop(cls.SESSION_KEY_VISITOR_ID, None)
            session.pop(cls.SESSION_KEY_ALLOCATION_TOKEN, None)
            session.save()
            return None, None

    @classmethod
    def extend_session_on_activity(cls, allocation: VisitorAllocation) -> None:
        """Heartbeat handler: keep a live session alive, promote a probation one.

        Allocation grants only a PROBATION_SECONDS provisional lease; the
        first heartbeat proves a JS-executing browser is attached and
        promotes it to the full session. Every later heartbeat re-extends,
        so an active visitor always has at least SESSION_LIFETIME_HOURS of
        runway — the "extended on activity" behavior the constants always
        documented but nothing implemented. max() semantics: never shortens
        an existing lease. Idle eviction is unaffected — it keys on
        ``last_activity`` (IDLE_TIMEOUT_MINUTES), which the heartbeat client
        stops feeding ~60s after the user goes inactive.
        """
        now = timezone.now()
        full_session = now + timedelta(hours=cls.SESSION_LIFETIME_HOURS)
        if allocation.expires_at is None or allocation.expires_at < full_session:
            allocation.expires_at = full_session
        allocation.last_activity = now
        allocation.save(update_fields=["expires_at", "last_activity"])

    @classmethod
    def _verify_slot_clean(cls, user: User, project: Project) -> bool:
        """Synchronous safety net: cheap filesystem check before handoff.

        Verifies the slot's workspace still looks like a freshly cloned
        template (marker present). This runs inline in the request so a
        dirty/broken slot is refused even if the async pipeline lied.
        """
        from pathlib import Path

        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        from .workspace_manager import verify_template_marker

        manager = get_project_filesystem_manager(user)
        project_path = Path(manager.base_path) / project.slug
        return verify_template_marker(project_path)

    @classmethod
    def _try_allocate_slot(
        cls, visitor_num: int, session, pool_size: int
    ) -> Tuple[Optional[Project], Optional[User]]:
        """
        Allocate one slot — ONLY if it is verified clean.

        Gate (audit fix #2): a slot is distributable only when its
        allocation row says ``workspace_ready=True`` (wiped + verified
        since the last visitor) and ``quarantined=False``, AND the
        synchronous template-marker check passes. The wipe itself runs
        at RELEASE time (async); nothing is cleaned inline here, so a
        Celery outage can never let a dirty slot through — it just
        keeps the slot out of circulation.
        """
        from django.db import IntegrityError

        # First verify the visitor user and project exist
        username = f"{cls.VISITOR_USER_PREFIX}{visitor_num:03d}"
        project_slug = "default-project"

        try:
            user = User.objects.get(username=username)
            project = Project.objects.get(slug=project_slug, owner=user)
        except (User.DoesNotExist, Project.DoesNotExist):
            logger.error(
                f"[VisitorPool] Visitor slot {visitor_num} user/project not found"
            )
            return None, None

        # Use select_for_update with skip_locked to avoid race conditions
        allocation = (
            VisitorAllocation.objects.filter(visitor_number=visitor_num)
            .select_for_update(skip_locked=True)
            .first()
        )

        if allocation is None:
            # Never reconciled → unverified. Boot reconciliation
            # (manage.py reconcile_visitor_slots) creates verified rows;
            # a rowless slot must not be served.
            logger.warning(
                f"[VisitorPool] Slot {visitor_num} has no allocation row "
                f"(unverified) — run reconcile_visitor_slots"
            )
            return None, None

        if allocation.quarantined:
            # NEVER serve a quarantined slot.
            return None, None

        now = timezone.now()

        if allocation.is_active:
            if is_allocation_stale(allocation, now):
                # Expired OR idle (visitor walked away without logging
                # out). The workspace is DIRTY — trigger the release
                # pipeline and refuse to serve it this request. Reclaiming
                # IDLE rows here (not just expired ones) means the pool
                # self-heals from serving traffic alone, so the periodic
                # celery reaper is no longer a single point of failure —
                # the failure mode that wedged prod at free=0 (2026-07-09).
                reason = (
                    "expired-lazy" if allocation.expires_at < now else "idle-lazy"
                )
                release_slot(allocation, reason=reason)
                return None, None
            # Genuinely live session — slot busy.
            return None, None

        if not allocation.workspace_ready:
            # Released but the wipe+verify has not completed (or Celery
            # is down). Not distributable.
            return None, None

        # Synchronous safety net before handoff.
        if not cls._verify_slot_clean(user, project):
            quarantine_slot(
                allocation,
                "sync pre-handoff check failed: template marker missing",
            )
            return None, None

        allocation_token = secrets.token_hex(32)
        # PROBATION lease, not the full session. The first heartbeat
        # promotes it to SESSION_LIFETIME_HOURS (extend_session_on_activity);
        # a client that never runs JS never beats, so it expires here and
        # the slot returns to the pool in minutes instead of an hour.
        expires_at = now + timedelta(seconds=cls.PROBATION_SECONDS)

        try:
            allocation.session_key = session.session_key or ""
            allocation.allocation_token = allocation_token
            allocation.expires_at = expires_at
            allocation.is_active = True
            # Record when THIS visitor got the slot. The field default only
            # fires on row creation, and slot rows are created once and
            # reused forever — on prod every row still read February, which
            # is why allocation age was unreadable during the 2026-07-14
            # incident.
            allocation.allocated_at = now
            # Start the idle clock NOW. is_allocation_stale() reclaims any
            # ACTIVE slot whose last_activity is older than
            # IDLE_TIMEOUT_MINUTES, so handing a visitor a slot without
            # resetting it hands them one that is ALREADY idle-stale: the
            # very next request sees is_active + an ancient last_activity
            # and evicts them with reason="idle-lazy". On prod every row
            # carried a last_activity days old (and an allocated_at from
            # February, auto_now_add so never refreshed), which made the
            # predicate permanently true — every slot was released within
            # seconds of being allocated, the pool sat at 0 allocatable,
            # and EVERY visitor fell through to readonly-visitor.
            allocation.last_activity = now
            # workspace_ready stays True: it was verified clean at
            # release time and is now in use by exactly one visitor.
            allocation.save()

            # Store in session
            session[cls.SESSION_KEY_PROJECT_ID] = project.id
            session[cls.SESSION_KEY_VISITOR_ID] = user.id
            session[cls.SESSION_KEY_ALLOCATION_TOKEN] = allocation_token
            session.pop(cls.SESSION_KEY_READONLY_REASON, None)
            session.save()

            logger.info(
                f"[VisitorPool] Allocated verified-clean visitor-{visitor_num:03d} "
                f"(expires_at={expires_at.isoformat()})"
            )
            return project, user

        except IntegrityError:
            # Race condition - another request allocated this slot
            logger.debug(
                f"[VisitorPool] Slot {visitor_num} taken by concurrent request"
            )
            return None, None

    @classmethod
    def deallocate_visitor(cls, session):
        """
        Free visitor slot (called when session expires or user signs up).

        Runs the release pipeline: the slot is marked not-ready and an
        async wipe+verify reset is enqueued; it is not reusable until
        the reset verifies clean (audit fix #3 — the expiry middleware
        calls this too, instead of just popping session keys).

        Args:
            session: Django session object
        """
        allocation_token = session.get(cls.SESSION_KEY_ALLOCATION_TOKEN)
        if not allocation_token:
            return

        try:
            allocation = VisitorAllocation.objects.get(
                allocation_token=allocation_token
            )
            release_slot(allocation, reason="deallocated")

            # Clear session
            session.pop(cls.SESSION_KEY_PROJECT_ID, None)
            session.pop(cls.SESSION_KEY_VISITOR_ID, None)
            session.pop(cls.SESSION_KEY_ALLOCATION_TOKEN, None)
            session.save()

            logger.info(
                f"[VisitorPool] Deallocated visitor-{allocation.visitor_number:03d}"
            )

        except VisitorAllocation.DoesNotExist:
            logger.warning(
                f"[VisitorPool] Allocation not found for token: {allocation_token[:8]}..."
            )

    @classmethod
    def get_pool_status(cls, pool_size: int) -> dict:
        """
        Get current pool status.

        Args:
            pool_size: Size of the visitor pool

        Returns:
            dict: {total, allocated, free, expired, quarantined, ready}

            ``free`` and ``ready`` are NOT interchangeable, and ``ready`` is
            the one that governs: allocation needs a slot that is unallocated
            AND workspace_ready AND not quarantined. ``free`` is merely
            total - occupied, so it counts slots that can never be handed out.
            Report ``ready`` to anyone asking "can I get a slot?" — a UI that
            showed ``free`` claimed spare capacity while every visitor was
            correctly downgraded to read-only (prod 2026-07-30).
        """
        now = timezone.now()
        total = pool_size

        # "Occupied" = a genuinely LIVE visitor session: ``is_active`` AND
        # neither expired nor idle. A stale row (``is_active`` with a
        # future ``expires_at`` but a weeks-old ``last_activity``) is NOT
        # occupied — it is reclaimable, so it counts as free. Counting only
        # ``expires_at`` (the old behaviour) let such zombie rows wedge the
        # pool at free=0 (prod 2026-07-09): nothing had extended
        # ``expires_at``, yet the idle dimension was ignored.
        occupied = (
            VisitorAllocation.objects.filter(is_active=True)
            .exclude(stale_allocation_q(now))
            .count()
        )

        expired = VisitorAllocation.objects.filter(
            is_active=True, expires_at__lte=now
        ).count()

        quarantined = VisitorAllocation.objects.filter(quarantined=True).count()
        ready = VisitorAllocation.objects.filter(
            quarantined=False, is_active=False, workspace_ready=True
        ).count()

        return {
            "total": total,
            "allocated": occupied,
            "free": max(0, total - occupied),
            "expired": expired,
            "quarantined": quarantined,
            "ready": ready,
        }
