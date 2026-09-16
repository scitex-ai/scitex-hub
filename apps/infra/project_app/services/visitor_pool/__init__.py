"""Read-only legacy allocation status API.

The public status collector imports :class:`VisitorPool` while historical
allocation rows remain in the database. Product allocation/session helpers were
removed with the authenticated-only domain.
"""

from .visitor_pool import DemoProjectPool, VisitorPool

__all__ = ["DemoProjectPool", "VisitorPool"]
