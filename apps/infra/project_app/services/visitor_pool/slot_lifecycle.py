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
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation

logger = logging.getLogger(__name__)

VISITOR_USER_PREFIX = "visitor-"

# Idle timeout: an ``is_active`` slot with no activity for this many
# minutes is reclaimable even if its hard ``expires_at`` has not passed.
# Single source of truth — the reaper (pool_cleanup), the allocator
# (pool_manager) and get_pool_status all derive "stale" from the helpers
# below so the three can never disagree. That disagreement is exactly
# what let zombie ``is_active`` rows wedge the pool at free=0 in prod
# (2026-07-09): nothing had extended ``expires_at``, yet the weeks-old
# ``last_activity`` (idle) dimension was ignored by the expiry-only
# checks, so the slots were neither counted free nor reclaimed.
IDLE_TIMEOUT_MINUTES = 30


def visitor_username(visitor_number: int) -> str:
    return f"{VISITOR_USER_PREFIX}{visitor_number:03d}"


def stale_allocation_q(now=None) -> Q:
    """Q selecting *reclaimable* rows among ``is_active=True`` allocations.

    A live visitor session is over — and its slot must be freed — when any
    of these hold:

    * ``expires_at`` is in the past (hard 1-hour session expiry), OR
    * ``last_activity`` is older than :data:`IDLE_TIMEOUT_MINUTES` (the
      visitor walked away without logging out), OR
    * it never sent a heartbeat (``last_activity`` is NULL) and was
      allocated longer ago than the idle timeout.

    Combine with ``is_active=True``; a row NOT matching this is a genuinely
    live session. A zombie row (``is_active`` with a *future* ``expires_at``
    but a weeks-old ``last_activity``) matches via the idle clause — the
    case the expiry-only checks missed.
    """
    if now is None:
        now = timezone.now()
    idle_cutoff = now - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    return (
        Q(expires_at__lt=now)
        | Q(last_activity__lt=idle_cutoff)
        | Q(last_activity__isnull=True, allocated_at__lt=idle_cutoff)
    )


def is_allocation_stale(allocation, now=None) -> bool:
    """Row-level mirror of :func:`stale_allocation_q` (expired OR idle)."""
    if now is None:
        now = timezone.now()
    idle_cutoff = now - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    if allocation.expires_at is not None and allocation.expires_at < now:
        return True
    if allocation.last_activity is not None:
        return allocation.last_activity < idle_cutoff
    return (
        allocation.allocated_at is not None and allocation.allocated_at < idle_cutoff
    )


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
    allocation: VisitorAllocation, *, gitea_client=None, clone_fn=None, run_cmd=None
) -> bool:
    """Run the full teardown+wipe+verify pipeline for one slot.

    On success the slot returns to the distributable pool
    (``workspace_ready=True``, quarantine cleared). On ANY failure the
    slot is quarantined and ``False`` is returned.

    ``run_cmd`` is the injectable subprocess boundary for the SLURM /
    apptainer container teardown (see ``container_teardown``); ``None``
    runs the real commands.

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
            user, gitea_client=gitea_client, clone_fn=clone_fn, run_cmd=run_cmd
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
