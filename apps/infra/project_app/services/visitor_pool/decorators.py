"""
Visitor Pool Decorators

Workspace lifecycle decorators that ensure visitor slots are always clean.

Two-layer protection against data leakage between visitors:
1. @reset_workspace_after  — cleans workspace on deallocation (normal path)
2. @ensure_clean_workspace — validates workspace is clean on allocation (safety net)

The safety net catches edge cases where deallocation cleanup didn't run:
server crash, Docker restart, NAS reboot, session expiry without request.
"""

import functools
import logging

from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


def reset_workspace_after(method):
    """Clean workspace after deallocation so slot is ready for next visitor.

    Applied to deallocate_visitor(). Resets the workspace immediately
    after marking the slot inactive, so the next allocation finds a
    clean workspace with no previous visitor's files.
    """

    @functools.wraps(method)
    def wrapper(cls, session, *args, **kwargs):
        # Capture visitor user before deallocation clears session
        from .pool_manager import PoolAllocator

        visitor_user_id = session.get(PoolAllocator.SESSION_KEY_VISITOR_ID)

        # Run the actual deallocation
        result = method(cls, session, *args, **kwargs)

        # Reset workspace after slot is freed
        if visitor_user_id:
            try:
                user = User.objects.get(id=visitor_user_id)
                from .workspace_manager import WorkspaceManager

                WorkspaceManager.reset_visitor_workspace(user)
                logger.info(
                    f"[VisitorPool] Workspace reset after deallocation: {user.username}"
                )
            except User.DoesNotExist:
                logger.warning(
                    f"[VisitorPool] User {visitor_user_id} not found for post-deallocation cleanup"
                )
            except Exception as e:
                logger.error(
                    f"[VisitorPool] Post-deallocation workspace reset failed: {e}",
                    exc_info=True,
                )

        return result

    return wrapper


def ensure_clean_workspace(method):
    """Safety net: validate workspace is clean before allocation.

    Applied to _try_allocate_slot(). If the slot was previously used
    (expired or deactivated) and the workspace wasn't cleaned (e.g.,
    server crash, Docker restart), reset it before giving it to the
    new visitor.

    This is the security boundary — no previous visitor's data must
    leak to the next visitor, regardless of how the slot was freed.
    """

    @functools.wraps(method)
    def wrapper(cls, visitor_num, session, pool_size, *args, **kwargs):
        from apps.infra.project_app.models import VisitorAllocation

        allocation = VisitorAllocation.objects.filter(
            visitor_number=visitor_num
        ).first()

        # If slot was previously used, ensure workspace is clean
        if allocation is not None and (
            not allocation.is_active
            or allocation.expires_at
            and allocation.expires_at < timezone.now()
        ):
            username = f"{cls.VISITOR_USER_PREFIX}{visitor_num:03d}"
            try:
                user = User.objects.get(username=username)
                from .workspace_manager import WorkspaceManager

                WorkspaceManager.reset_visitor_workspace(user)
                logger.info(
                    f"[VisitorPool] Workspace validated clean before allocation: {username}"
                )
            except User.DoesNotExist:
                pass
            except Exception as e:
                logger.error(
                    f"[VisitorPool] Pre-allocation workspace validation failed for {username}: {e}",
                    exc_info=True,
                )

        return method(cls, visitor_num, session, pool_size, *args, **kwargs)

    return wrapper
