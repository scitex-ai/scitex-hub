"""
Visitor Workspace Async Tasks

Runs the wipe+verify reset for a RELEASED visitor slot in a Celery
worker. Enqueued by the release pipeline
(``visitor_pool.slot_lifecycle.release_slot``) whenever a slot is
deallocated, expires, idles out, or is claimed on signup.

Security contract (visitor-slot isolation audit 2026-07-07): the slot
was already marked ``workspace_ready=False`` at release, so it cannot
be allocated while this task is pending or running — even if Celery is
down entirely, the slot simply stays out of circulation. Only a reset
that VERIFIES clean flips ``workspace_ready`` back to ``True``; any
failure QUARANTINES the slot (fail loud, never redistribute).
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def reset_visitor_slot(self, allocation_id: int):
    """
    Async wipe + verify for a released visitor slot.

    On success the slot returns to the distributable pool. On failure
    it is quarantined immediately (so a half-wiped workspace can never
    be served) and the task retries — a later success un-quarantines.

    Args:
        allocation_id: PK of the VisitorAllocation row.
    """
    from apps.infra.project_app.models import VisitorAllocation
    from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
        reset_and_verify_slot,
    )

    try:
        allocation = VisitorAllocation.objects.get(id=allocation_id)
    except VisitorAllocation.DoesNotExist:
        logger.error(f"[VisitorPool] Celery task: allocation {allocation_id} not found")
        return

    if allocation.is_active:
        # Re-allocated in the meantime (only possible after a verified
        # reset already ran) — never wipe under a live visitor.
        logger.warning(
            f"[VisitorPool] Celery task: allocation {allocation_id} is active, "
            f"skipping reset"
        )
        return

    if allocation.workspace_ready and not allocation.quarantined:
        logger.info(
            f"[VisitorPool] Celery task: allocation {allocation_id} already "
            f"verified clean, skipping"
        )
        return

    ok = reset_and_verify_slot(allocation)
    if not ok:
        # reset_and_verify_slot already quarantined the slot and logged
        # loudly. Retry for transient failures (Gitea blip, NFS hiccup);
        # a later success clears the quarantine.
        raise self.retry(
            exc=RuntimeError(
                f"visitor slot reset failed for allocation {allocation_id} "
                f"(slot quarantined)"
            )
        )
