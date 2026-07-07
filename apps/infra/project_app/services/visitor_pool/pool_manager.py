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

from .slot_lifecycle import quarantine_slot, release_slot

logger = logging.getLogger(__name__)


class PoolAllocator:
    """Manages allocation of visitor slots from the pool."""

    VISITOR_USER_PREFIX = "visitor-"
    POOL_SIZE = None  # Will be set by VisitorPool
    SESSION_LIFETIME_HOURS = 1  # Base session time (extended on activity)
    SESSION_EXTENSION_MINUTES = 30  # Extend by this much on activity
    IDLE_TIMEOUT_MINUTES = 30  # Release slot if idle longer than this
    SESSION_KEY_PROJECT_ID = "visitor_project_id"
    SESSION_KEY_VISITOR_ID = "visitor_user_id"
    SESSION_KEY_ALLOCATION_TOKEN = "visitor_allocation_token"
    SESSION_KEY_READONLY_REASON = "visitor_readonly_reason"

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

        # Find free visitor slot
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
            reason = "pool_full"
            logger.warning(
                f"[VisitorPool] Pool exhausted - all {pool_size} slots in use"
            )
        else:
            reason = "no_ready_slot"
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

        if allocation.is_active and allocation.expires_at >= now:
            # Slot busy.
            return None, None

        if allocation.is_active and allocation.expires_at < now:
            # Expired but never released (visitor walked away, sweep has
            # not run yet). The workspace is DIRTY — trigger the release
            # pipeline and refuse to serve it this request.
            release_slot(allocation, reason="expired-lazy")
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
        expires_at = now + timedelta(hours=cls.SESSION_LIFETIME_HOURS)

        try:
            allocation.session_key = session.session_key or ""
            allocation.allocation_token = allocation_token
            allocation.expires_at = expires_at
            allocation.is_active = True
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
            dict: {total, allocated, free, expired}
        """
        total = pool_size
        active_allocations = VisitorAllocation.objects.filter(
            is_active=True, expires_at__gt=timezone.now()
        ).count()

        expired = VisitorAllocation.objects.filter(
            is_active=True, expires_at__lte=timezone.now()
        ).count()

        quarantined = VisitorAllocation.objects.filter(quarantined=True).count()
        ready = VisitorAllocation.objects.filter(
            quarantined=False, is_active=False, workspace_ready=True
        ).count()

        return {
            "total": total,
            "allocated": active_allocations,
            "free": total - active_allocations,
            "expired": expired,
            "quarantined": quarantined,
            "ready": ready,
        }
