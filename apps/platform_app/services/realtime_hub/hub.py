"""
RealtimeHub — broadcasts messages to WebSocket subscribers via Django Channels.

Group naming convention:
    platform_{app_name}_{channel}_{resource_id}

This keeps groups scoped per app + channel + resource so that multiple
apps can share the same Channels layer without name collisions.
"""

import re
from typing import Any, Dict

from channels.layers import get_channel_layer


class RealtimeHub:
    """Thin wrapper around Django Channels group messaging.

    All methods are async so they can be called from async consumers
    or async Django views (via sync_to_async in sync contexts).
    """

    # Maximum length for a single group-name segment (Channels / Redis limit).
    _MAX_SEGMENT = 80

    # ------------------------------------------------------------------ helpers

    def get_group_name(self, app_name: str, channel: str, resource_id: str) -> str:
        """Return a consistent, safe Channels group name.

        Characters outside [a-zA-Z0-9_.-] are replaced with underscores so the
        name is valid for every Channels backend.
        """
        raw = f"platform_{app_name}_{channel}_{resource_id}"
        safe = re.sub(r"[^a-zA-Z0-9_.\-]", "_", raw)
        return safe[: self._MAX_SEGMENT]

    # ----------------------------------------------------------------- actions

    async def broadcast(
        self,
        app_name: str,
        channel: str,
        resource_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Send *message* to every subscriber of the (app, channel, resource) group.

        Args:
            app_name:    Identifier of the originating app (e.g. ``"notes_app"``).
            channel:     Logical channel name (e.g. ``"document"``).
            resource_id: Primary key / identifier of the resource.
            message:     Arbitrary JSON-serialisable payload to forward.
        """
        layer = get_channel_layer()
        group = self.get_group_name(app_name, channel, resource_id)
        await layer.group_send(
            group,
            {
                "type": "platform_message",
                "app_name": app_name,
                "channel": channel,
                "resource_id": resource_id,
                "message": message,
            },
        )

    async def presence_join(
        self,
        app_name: str,
        channel: str,
        resource_id: str,
        user: Any,
    ) -> None:
        """Announce that *user* joined (app, channel, resource).

        Args:
            user: Django user object.  ``str(user)`` is used as display name.
        """
        await self.broadcast(
            app_name,
            channel,
            resource_id,
            {
                "type": "presence",
                "event": "join",
                "user": str(user),
            },
        )

    async def presence_leave(
        self,
        app_name: str,
        channel: str,
        resource_id: str,
        user: Any,
    ) -> None:
        """Announce that *user* left (app, channel, resource).

        Args:
            user: Django user object.  ``str(user)`` is used as display name.
        """
        await self.broadcast(
            app_name,
            channel,
            resource_id,
            {
                "type": "presence",
                "event": "leave",
                "user": str(user),
            },
        )
