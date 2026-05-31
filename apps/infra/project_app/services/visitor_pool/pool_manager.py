"""
Visitor Pool Allocation and Deallocation Management

Handles allocation of visitor slots from the pre-allocated pool and
deallocation when sessions expire or users sign up.

Allocation uses a 2-phase approach:
  Phase 1 (synchronous, fast): DB slot allocation + set expires_at + login
  Phase 2 (async, Celery):     clone_template + workspace setup
This prevents clone_template() (5-30s) from blocking the HTTP request.
"""

import logging
import secrets
from datetime import timedelta
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation

from .decorators import reset_workspace_after

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

    @classmethod
    def _check_table_exists(cls) -> bool:
        """Check if VisitorAllocation table exists.

        Uses Django's backend-agnostic introspection rather than a raw
        ``information_schema`` query: ``information_schema`` does not exist on
        SQLite, so the raw query silently failed and forced the DemoProjectPool
        fallback on SQLite (incl. the CI test database).
        """
        try:
            from django.db import connection

            table = VisitorAllocation._meta.db_table
            with connection.cursor() as cursor:
                return table in connection.introspection.table_names(cursor)
        except Exception:
            return False

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

        # Pool exhausted
        logger.warning(f"[VisitorPool] Pool exhausted - all {pool_size} slots in use")
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
    def _try_allocate_slot(
        cls, visitor_num: int, session, pool_size: int
    ) -> Tuple[Optional[Project], Optional[User]]:
        """
        Phase 1 (synchronous): allocate DB slot and set expires_at.

        Workspace initialization (clone_template) is deferred to a Celery
        task (Phase 2) so the HTTP request returns immediately.
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

        # Slot is free if: no allocation, expired, or inactive
        if (
            allocation is None
            or not allocation.is_active
            or allocation.expires_at < timezone.now()
        ):
            allocation_token = secrets.token_hex(32)
            expires_at = timezone.now() + timedelta(hours=cls.SESSION_LIFETIME_HOURS)

            try:
                if allocation:
                    # Update existing allocation atomically (no delete/create race)
                    allocation.session_key = session.session_key or ""
                    allocation.allocation_token = allocation_token
                    allocation.expires_at = expires_at
                    allocation.is_active = True
                    allocation.workspace_ready = False
                    allocation.save()
                else:
                    # Create new allocation
                    allocation = VisitorAllocation.objects.create(
                        visitor_number=visitor_num,
                        session_key=session.session_key or "",
                        allocation_token=allocation_token,
                        expires_at=expires_at,
                        is_active=True,
                        workspace_ready=False,
                    )

                # Store in session
                session[cls.SESSION_KEY_PROJECT_ID] = project.id
                session[cls.SESSION_KEY_VISITOR_ID] = user.id
                session[cls.SESSION_KEY_ALLOCATION_TOKEN] = allocation_token
                session.save()

                logger.info(
                    f"[VisitorPool] Phase 1 complete: allocated visitor-{visitor_num:03d} "
                    f"(expires_at={expires_at.isoformat()}), queuing workspace init"
                )

                # Phase 2: queue async workspace initialization.
                # Best-effort: a missing/unreachable Celery broker must not undo
                # the Phase 1 allocation that already succeeded above (and must
                # not hang the synchronous request). The workspace is created
                # lazily on first use if the task never runs.
                from apps.infra.project_app.tasks import (
                    initialize_visitor_workspace,
                )

                try:
                    initialize_visitor_workspace.delay(allocation.id)
                except Exception as exc:
                    logger.warning(
                        "[VisitorPool] Could not queue workspace init for "
                        "visitor-%03d (broker unavailable?): %s",
                        visitor_num,
                        exc,
                    )

                return project, user

            except IntegrityError:
                # Race condition - another request allocated this slot
                logger.debug(
                    f"[VisitorPool] Slot {visitor_num} taken by concurrent request"
                )
                return None, None

        return None, None

    @classmethod
    @reset_workspace_after
    def deallocate_visitor(cls, session):
        """
        Free visitor slot (called when session expires or user signs up).

        Decorated with @reset_workspace_after to clean workspace immediately
        so the slot is ready for the next visitor with no data leakage.

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
            allocation.is_active = False
            allocation.save()

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

        return {
            "total": total,
            "allocated": active_allocations,
            "free": total - active_allocations,
            "expired": expired,
        }
