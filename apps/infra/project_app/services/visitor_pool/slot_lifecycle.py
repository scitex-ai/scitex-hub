"""
Visitor slot lifecycle — release, quarantine, verified re-clean.

Security state machine (visitor-slot isolation audit 2026-07-07):

* A slot is DISTRIBUTABLE only when ``workspace_ready=True`` and
  ``quarantined=False`` — i.e. its workspace was wiped, verified empty,
  re-cloned, and the clone verified since the last visitor used it.
* Releasing a slot (deallocation, expiry, idle sweep, signup claim)
  immediately drops ``workspace_ready`` to ``False`` and enqueues the
  async reset. Until the reset VERIFIES clean, allocation refuses the
  slot — so a Celery outage can never cause a dirty slot to be served
  (it only shrinks the pool; overflow goes to readonly-visitor).
* Any reset failure QUARANTINES the slot: it is never allocated again
  until ``manage.py reconcile_visitor_slots`` re-cleans and re-verifies
  it.
"""

import logging
import secrets

from django.db import transaction
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation

logger = logging.getLogger(__name__)

VISITOR_USER_PREFIX = "visitor-"


def visitor_username(visitor_number: int) -> str:
    return f"{VISITOR_USER_PREFIX}{visitor_number:03d}"


def quarantine_slot(allocation: VisitorAllocation, reason: str) -> None:
    """Mark a slot quarantined so allocation NEVER picks it.

    Loud by design: this always logs at CRITICAL — a quarantined slot
    means a visitor-data leak was prevented but the pool lost capacity
    and needs `manage.py reconcile_visitor_slots` (or operator action).
    """
    allocation.quarantined = True
    allocation.quarantined_at = timezone.now()
    allocation.quarantine_reason = reason[:2000]
    allocation.is_active = False
    allocation.workspace_ready = False
    allocation.save(
        update_fields=[
            "quarantined",
            "quarantined_at",
            "quarantine_reason",
            "is_active",
            "workspace_ready",
        ]
    )
    logger.critical(
        f"[VisitorPool] QUARANTINED slot visitor-{allocation.visitor_number:03d}: "
        f"{reason} — slot will not be redistributed until re-verified clean "
        f"(manage.py reconcile_visitor_slots)"
    )


def get_or_create_allocation(visitor_number: int) -> VisitorAllocation:
    """Fetch (or create, in an unverified state) the slot's allocation row."""
    allocation = VisitorAllocation.objects.filter(
        visitor_number=visitor_number
    ).first()
    if allocation is None:
        allocation = VisitorAllocation.objects.create(
            visitor_number=visitor_number,
            session_key="",
            allocation_token=secrets.token_hex(32),
            expires_at=timezone.now(),
            is_active=False,
            workspace_ready=False,
        )
    return allocation


def release_slot(allocation: VisitorAllocation, reason: str = "released") -> None:
    """Release pipeline: free the slot and make it unusable until re-verified.

    1. ``is_active=False`` + ``workspace_ready=False`` — the slot is out
       of circulation immediately (allocation's ready gate refuses it).
    2. Enqueue the async wipe+verify reset. Only the reset flipping
       ``workspace_ready`` back to ``True`` returns the slot to the pool.

    Enqueue failures (broker down) are logged loudly but NOT fatal: the
    slot simply stays not-ready, which is the safe direction. The boot
    reconciliation / periodic sweep will pick it up.
    """
    allocation.is_active = False
    allocation.workspace_ready = False
    allocation.save(update_fields=["is_active", "workspace_ready"])
    logger.info(
        f"[VisitorPool] Released slot visitor-{allocation.visitor_number:03d} "
        f"({reason}); reset enqueued, not reusable until re-verified"
    )

    allocation_id = allocation.id

    def _enqueue():
        try:
            from apps.infra.project_app.tasks import reset_visitor_slot

            reset_visitor_slot.delay(allocation_id)
        except Exception as exc:
            logger.critical(
                f"[VisitorPool] Could not enqueue reset for allocation "
                f"{allocation_id}: {exc} — slot stays workspace_ready=False "
                f"(safe) until reconcile_visitor_slots runs"
            )

    transaction.on_commit(_enqueue)


def reset_and_verify_slot(
    allocation: VisitorAllocation, *, gitea_client=None, clone_fn=None
) -> bool:
    """Run the full wipe+verify pipeline for one slot.

    On success the slot returns to the distributable pool
    (``workspace_ready=True``, quarantine cleared). On ANY failure the
    slot is quarantined and ``False`` is returned.

    Never resets a slot that is actively allocated (would wipe files
    under a live visitor).
    """
    from django.contrib.auth.models import User

    from .workspace_manager import WorkspaceManager

    allocation.refresh_from_db()
    if allocation.is_active and allocation.expires_at > timezone.now():
        logger.warning(
            f"[VisitorPool] Refusing reset of ACTIVE slot "
            f"visitor-{allocation.visitor_number:03d}"
        )
        return False

    username = visitor_username(allocation.visitor_number)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        quarantine_slot(allocation, f"visitor user {username} missing")
        return False

    try:
        WorkspaceManager.reset_visitor_workspace(
            user, gitea_client=gitea_client, clone_fn=clone_fn
        )
    except Exception as exc:
        quarantine_slot(allocation, f"reset failed: {exc}")
        return False

    allocation.refresh_from_db()
    allocation.quarantined = False
    allocation.quarantined_at = None
    allocation.quarantine_reason = ""
    allocation.is_active = False
    allocation.workspace_ready = True
    allocation.save(
        update_fields=[
            "quarantined",
            "quarantined_at",
            "quarantine_reason",
            "is_active",
            "workspace_ready",
        ]
    )
    logger.info(
        f"[VisitorPool] Slot visitor-{allocation.visitor_number:03d} verified "
        f"clean and returned to pool"
    )
    return True


# EOF
