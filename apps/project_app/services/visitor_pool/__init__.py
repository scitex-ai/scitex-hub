"""
Visitor Pool Module

Manages pre-allocated visitor accounts for temporary access.

Public API:
- VisitorPool: Main class for pool management
- DemoProjectPool: Alias for backward compatibility
"""

from .visitor_pool import VisitorPool, DemoProjectPool

__all__ = [
    "VisitorPool",
    "DemoProjectPool",
]
