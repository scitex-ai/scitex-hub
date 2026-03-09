"""
RealtimeHub — Public API.

Usage:
    from apps.infra.platform_app.services.realtime_hub import RealtimeHub

    hub = RealtimeHub()
    await hub.broadcast("my_app", "notes", "uuid-123", {"type": "update", "data": ...})
"""

from .hub import RealtimeHub

__all__ = ["RealtimeHub"]
