"""
PlatformRealtimeConsumer — generic WebSocket consumer for real-time updates.

URL pattern (register in routing.py):
    ws/platform/realtime/<app>/<channel>/<resource_id>/

Clients subscribe by connecting to the URL for a specific resource.
The server pushes any broadcast message to all connected subscribers.
"""

import json

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.platform_app.services.realtime_hub import RealtimeHub

_hub = RealtimeHub()


class PlatformRealtimeConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer that subscribes a browser to platform realtime events.

    URL kwargs expected:
        app         — app_name segment
        channel     — logical channel name
        resource_id — resource identifier (UUID string or slug)
    """

    # ----------------------------------------------------------------- connect

    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.app_name = self.scope["url_route"]["kwargs"]["app"]
        self.channel_name_param = self.scope["url_route"]["kwargs"]["channel"]
        self.resource_id = self.scope["url_route"]["kwargs"]["resource_id"]
        self.user = user

        self.group_name = _hub.get_group_name(
            self.app_name, self.channel_name_param, self.resource_id
        )

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Announce presence to the group.
        await _hub.presence_join(
            self.app_name, self.channel_name_param, self.resource_id, user
        )

    # -------------------------------------------------------------- disconnect

    async def disconnect(self, code: int) -> None:
        if not hasattr(self, "group_name"):
            return

        await _hub.presence_leave(
            self.app_name, self.channel_name_param, self.resource_id, self.user
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ----------------------------------------------------------------- receive

    async def receive(self, text_data=None, bytes_data=None) -> None:
        """Handle messages sent by the connected browser client.

        Clients may push messages that are re-broadcast to the group,
        enabling simple peer-to-peer signalling through the server.
        """
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        # Re-broadcast client message to the whole group.
        await _hub.broadcast(
            self.app_name,
            self.channel_name_param,
            self.resource_id,
            data,
        )

    # ---------------------------------------------------- group message handler

    async def platform_message(self, event: dict) -> None:
        """Forward a group_send message to the connected WebSocket client.

        Django Channels dispatches group messages to the handler whose name
        matches the ``type`` field (dots replaced with underscores).
        """
        await self.send(
            text_data=json.dumps(
                {
                    "app": event.get("app_name"),
                    "channel": event.get("channel"),
                    "resource_id": event.get("resource_id"),
                    "message": event.get("message"),
                }
            )
        )

    # ----------------------------------------------------------------- helpers

    async def _send_error(self, detail: str) -> None:
        await self.send(text_data=json.dumps({"type": "error", "detail": detail}))
