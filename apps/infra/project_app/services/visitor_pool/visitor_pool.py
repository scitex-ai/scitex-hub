"""Legacy visitor-allocation status adapter.

Allocation is retired. This read-only adapter remains temporarily because the
public status surface still reads historical ``VisitorAllocation`` rows. It
must not allocate, mutate, reset, or claim a project.
"""

import os

from .pool_health import measure_pool


class VisitorPool:
    """Read-only compatibility surface for public status collection."""

    POOL_SIZE = int(os.environ.get("SCITEX_HUB_VISITOR_POOL_SIZE", 4))
    SESSION_KEY_ALLOCATION_TOKEN = "visitor_allocation_token"

    @classmethod
    def get_pool_status(cls) -> dict:
        return measure_pool(cls.POOL_SIZE)


DemoProjectPool = VisitorPool
