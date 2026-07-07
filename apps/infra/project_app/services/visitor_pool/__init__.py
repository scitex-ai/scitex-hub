"""
Visitor Pool Module

Manages pre-allocated visitor accounts for temporary access.

Public API:
- VisitorPool: Main class for pool management
- DemoProjectPool: Alias for backward compatibility
- Session-role model (card hub-visitor-ux-allapps): get_session_role /
  get_user_role map every request to exactly one of
  anonymous | readonly_visitor | visitor | user, and
  readonly_write_rejection() is the canonical structured 403 for
  write attempts by readonly visitors.
"""

from .session_role import (
    READONLY_REJECTION_REASON,
    ROLE_ANONYMOUS,
    ROLE_READONLY_VISITOR,
    ROLE_USER,
    ROLE_VISITOR,
    SESSION_KEY_READONLY_NOTICE,
    get_session_role,
    get_user_role,
    is_readonly_visitor,
    is_visitor_session,
    readonly_write_rejection,
)
from .visitor_pool import DemoProjectPool, VisitorPool

__all__ = [
    "VisitorPool",
    "DemoProjectPool",
    "READONLY_REJECTION_REASON",
    "ROLE_ANONYMOUS",
    "ROLE_READONLY_VISITOR",
    "ROLE_USER",
    "ROLE_VISITOR",
    "SESSION_KEY_READONLY_NOTICE",
    "get_session_role",
    "get_user_role",
    "is_readonly_visitor",
    "is_visitor_session",
    "readonly_write_rejection",
]
