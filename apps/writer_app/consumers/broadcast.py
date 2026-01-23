"""
Broadcast event handlers for WriterConsumer.
Handles sending events to all clients in a room.
"""

import json


class BroadcastMixin:
    """Mixin providing broadcast event handler methods for WriterConsumer."""

    async def user_joined(self, event):
        """Broadcast user joined to all clients."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_joined",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_left(self, event):
        """Broadcast user left to all clients."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_left",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def text_change(self, event):
        """Broadcast text change to all clients except sender."""
        if event.get("sender_channel") != self.channel_name:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "text_change",
                        "section": event.get("section"),
                        "section_id": event.get("section_id"),
                        "operation": event["operation"],
                        "user_id": event["user_id"],
                        "username": event.get("username"),
                        "timestamp": event["timestamp"],
                    }
                )
            )

    async def cursor_update(self, event):
        """Broadcast cursor position to all clients except sender."""
        if event.get("sender_channel") != self.channel_name:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "cursor_update",
                        "section": event["section"],
                        "position": event["position"],
                        "user_id": event["user_id"],
                        "username": event["username"],
                    }
                )
            )

    async def section_locked(self, event):
        """Broadcast section lock to all clients."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "section_locked",
                    "section": event["section"],
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def section_unlocked(self, event):
        """Broadcast section unlock to all clients."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "section_unlocked",
                    "section": event["section"],
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_undone(self, event):
        """Broadcast user undo action to all clients."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_undone",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "section_id": event["section_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_redone(self, event):
        """Broadcast user redo action to all clients."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_redone",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "section_id": event["section_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )
