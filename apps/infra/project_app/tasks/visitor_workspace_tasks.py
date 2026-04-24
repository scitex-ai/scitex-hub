"""
Visitor Workspace Async Tasks

Phase 2 of visitor allocation: clone template and set up workspace
in a Celery worker so the HTTP request is not blocked.

Phase 1 (synchronous) allocates the DB slot, sets expires_at, and
logs the user in.  Phase 2 (this module) runs the slow clone_template()
call in the background and marks workspace_ready=True when done.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def initialize_visitor_workspace(self, allocation_id: int):
    """
    Async workspace initialization (Phase 2).

    Resets the visitor workspace (clone template, clear data) and marks
    the allocation as workspace_ready=True.  If this fails, the error
    is logged and the allocation stays workspace_ready=False so the UI
    can show an honest error -- NO fallbacks.

    Args:
        allocation_id: PK of the VisitorAllocation row.
    """
    from django.contrib.auth.models import User

    from apps.infra.project_app.models import VisitorAllocation
    from apps.infra.project_app.services.visitor_pool.workspace_manager import (
        WorkspaceManager,
    )

    try:
        allocation = VisitorAllocation.objects.get(id=allocation_id)
    except VisitorAllocation.DoesNotExist:
        logger.error(f"[VisitorPool] Celery task: allocation {allocation_id} not found")
        return

    if not allocation.is_active:
        logger.warning(
            f"[VisitorPool] Celery task: allocation {allocation_id} already inactive, skipping"
        )
        return

    visitor_num = allocation.visitor_number
    username = f"visitor-{visitor_num:03d}"

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.error(f"[VisitorPool] Celery task: user {username} not found")
        return

    try:
        WorkspaceManager.reset_visitor_workspace(user)
        allocation.refresh_from_db()
        allocation.workspace_ready = True
        allocation.save(update_fields=["workspace_ready"])
        logger.info(
            f"[VisitorPool] Celery task: workspace ready for {username} "
            f"(allocation {allocation_id})"
        )
    except Exception as exc:
        logger.error(
            f"[VisitorPool] Celery task: workspace init failed for {username}: {exc}",
            exc_info=True,
        )
        # Retry if retries remain
        raise self.retry(exc=exc)
