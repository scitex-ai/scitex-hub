"""
Visitor Pool Manager

Pre-allocated visitor accounts for visitor users.
Each visitor gets a default project that can be claimed on signup.

Architecture:
- Configurable pool size via SCITEX_HUB_VISITOR_POOL_SIZE env var (default: 4)
- Allocation: Session-based with security token (1h lifetime)
- Signup: Transfer project ownership (visitor → real user)
- Reset: Clear workspace, free slot back to pool
"""

import os
from typing import Optional, Tuple

from django.contrib.auth.models import User

from apps.infra.project_app.models import Project

from .pool_cleanup import PoolCleanup
from .pool_initialization import PoolInitializer
from .pool_manager import PoolAllocator


class VisitorPool:
    """
    Manages fixed pool of visitor accounts and default projects.

    Pool Size: 4 concurrent visitors (rotated with 1h session lifetime)
    Naming: visitor-001 to visitor-004

    With 1-hour sessions, 4 slots support up to 96 visitors per day.
    When visitors sign up, their data is automatically migrated to their new account.
    Slots are automatically freed and reused when sessions expire.

    Read-only visitor: A shared account for when the pool is full.
    """

    VISITOR_USER_PREFIX = "visitor-"
    DEFAULT_PROJECT_PREFIX = "default-project-"
    READONLY_VISITOR_USERNAME = "readonly-visitor"
    POOL_SIZE = int(os.environ.get("SCITEX_HUB_VISITOR_POOL_SIZE", 4))
    SESSION_LIFETIME_HOURS = 1
    SESSION_KEY_PROJECT_ID = "visitor_project_id"
    SESSION_KEY_VISITOR_ID = "visitor_user_id"
    SESSION_KEY_ALLOCATION_TOKEN = "visitor_allocation_token"

    @classmethod
    def initialize_pool(cls, pool_size: int = None) -> int:
        """
        Create visitor pool (visitor-001 to visitor-004 by default).

        Run once during deployment: python manage.py create_visitor_pool

        Returns:
            int: Number of visitor accounts created
        """
        if pool_size is None:
            pool_size = cls.POOL_SIZE

        # Update pool allocator with actual pool size
        PoolAllocator.POOL_SIZE = pool_size

        return PoolInitializer.initialize_pool(pool_size)

    @classmethod
    def allocate_visitor(cls, session) -> Tuple[Optional[Project], Optional[User]]:
        """
        Allocate a free visitor slot to the session.

        Uses database locking to prevent race conditions.
        Falls back to DemoProjectPool if VisitorAllocation table not created yet.

        Returns:
            tuple: (Project, User) or (None, None) if pool exhausted
        """
        # Update pool allocator with actual pool size
        PoolAllocator.POOL_SIZE = cls.POOL_SIZE
        return PoolAllocator.allocate_visitor(session, cls.POOL_SIZE)

    @classmethod
    def deallocate_visitor(cls, session):
        """
        Free visitor slot (called when session expires or user signs up).

        Args:
            session: Django session object
        """
        PoolAllocator.deallocate_visitor(session)

    @classmethod
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
        return PoolCleanup.claim_project_on_signup(session, new_user)

    @classmethod
    def cleanup_expired_allocations(cls) -> int:
        """
        Free visitor slots with expired sessions.

        Returns:
            int: Number of slots freed
        """
        return PoolCleanup.cleanup_expired_allocations()

    @classmethod
    def get_pool_status(cls) -> dict:
        """
        Get current pool status.

        Returns:
            dict: {total, allocated, free, expired}
        """
        return PoolAllocator.get_pool_status(cls.POOL_SIZE)

    @classmethod
    def reset_all_project_directories(cls) -> int:
        """
        Reset all visitor project directories to default template state.

        This removes existing directories and re-copies the template.
        Used when re-initializing the pool in development.

        Returns:
            int: Number of directories reset
        """
        return PoolInitializer.reset_all_project_directories(cls.POOL_SIZE)


# For backward compatibility during migration
DemoProjectPool = VisitorPool
