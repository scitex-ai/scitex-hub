"""
Visitor Pool Cleanup and Maintenance

Handles cleanup of expired allocations and project claiming on signup.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from apps.project_app.models import Project, VisitorAllocation

logger = logging.getLogger(__name__)


class PoolCleanup:
    """Handles cleanup and maintenance operations."""

    VISITOR_USER_PREFIX = "visitor-"

    @classmethod
    def cleanup_expired_allocations(cls) -> int:
        """
        Free visitor slots with expired sessions.

        Returns:
            int: Number of slots freed
        """
        expired = VisitorAllocation.objects.filter(
            is_active=True, expires_at__lt=timezone.now()
        )

        count = 0
        for allocation in expired:
            allocation.is_active = False
            allocation.save()
            count += 1
            logger.info(
                f"[VisitorPool] Freed expired slot: visitor-{allocation.visitor_number:03d}"
            )

        return count

    @classmethod
    @transaction.atomic
    def claim_project_on_signup(cls, session, new_user: User) -> Optional[Project]:
        """
        Transfer visitor's default project to newly signed-up user.

        Called during signup to preserve visitor's work.

        Args:
            session: Django session with visitor allocation
            new_user: Newly created user account

        Returns:
            Optional[Project]: Transferred project or None
        """
        from .pool_manager import PoolAllocator

        visitor_project_id = session.get(PoolAllocator.SESSION_KEY_PROJECT_ID)
        allocation_token = session.get(PoolAllocator.SESSION_KEY_ALLOCATION_TOKEN)

        if not visitor_project_id or not allocation_token:
            logger.warning(
                f"[VisitorPool] No visitor project to claim for user {new_user.username}"
            )
            return None

        try:
            # Get visitor project
            project = Project.objects.get(id=visitor_project_id)
            old_owner = project.owner

            # Verify it's a default project
            if project.slug != "default-project":
                logger.error(
                    f"[VisitorPool] Project {project.id} is not a default project (slug: {project.slug})"
                )
                return None

            # Transfer ownership
            project.owner = new_user
            project.save()

            # Update filesystem ownership
            cls._move_project_files(old_owner, new_user, project)

            # Deallocate visitor slot
            PoolAllocator.deallocate_visitor(session)

            # Reset visitor workspace for next user
            from .workspace_manager import WorkspaceManager
            WorkspaceManager.reset_visitor_workspace(old_owner)

            logger.info(
                f"[VisitorPool] Claimed project {project.slug} for user {new_user.username}"
            )
            return project

        except Project.DoesNotExist:
            logger.error(f"[VisitorPool] Project {visitor_project_id} not found")
            return None
        except Exception as e:
            logger.error(f"[VisitorPool] Error claiming project: {e}", exc_info=True)
            return None

    @classmethod
    def _move_project_files(cls, old_owner: User, new_user: User, project: Project):
        """Move project files from visitor to new user's directory."""
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        old_manager = get_project_filesystem_manager(old_owner)
        new_manager = get_project_filesystem_manager(new_user)

        old_path = old_manager.get_project_root_path(project)
        if old_path and old_path.exists():
            # Move directory from visitor space to user space
            new_path = new_manager.base_path / new_user.username / project.slug
            new_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(old_path), str(new_path))

            # Update data_location
            project.data_location = str(new_path.relative_to(new_manager.base_path))
            project.save()

            logger.info(
                f"[VisitorPool] Moved project from {old_path} to {new_path}"
            )
