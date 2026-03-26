"""
CommsConsumer -- WebSocket consumer for real-time messaging.

URL: ws/comms/channel/<channel_slug>/

Client -> Server:
    {"type": "message.send", "text": "hello", "parent_id": null}
    {"type": "message.edit", "message_id": 42, "text": "updated"}
    {"type": "typing.start"}
    {"type": "typing.stop"}
    {"type": "mark_read"}

Server -> Client:
    {"type": "message.new", "message": {...}}
    {"type": "message.edited", "message": {...}}
    {"type": "typing.indicator", "participant": {...}, "is_typing": true}
    {"type": "presence.update", "participant": {...}, "is_online": true}
"""

import hashlib
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from apps.infra.accounts_app.models import APIKey
from apps.workspace.comms_app.models import (
    Channel,
    ChannelMembership,
    Message,
    Participant,
)


class CommsConsumer(AsyncWebsocketConsumer):
    """Real-time messaging consumer for comms channels."""

    # ----------------------------------------------------------------- connect

    async def connect(self):
        """Authenticate, resolve participant, join channel group."""
        self.channel_slug = self.scope["url_route"]["kwargs"]["channel_slug"]
        self.group_name = f"comms_channel_{self.channel_slug}"

        # Authenticate: agent token or Django session
        self.participant = await self._resolve_participant()
        if self.participant is None:
            await self.close()
            return

        # Verify channel exists
        try:
            self.comms_channel = await Channel.objects.aget(
                slug=self.channel_slug, is_archived=False
            )
        except Channel.DoesNotExist:
            await self.close()
            return

        # Verify membership
        has_membership = await ChannelMembership.objects.filter(
            channel=self.comms_channel, participant=self.participant
        ).aexists()
        if not has_membership:
            await self.close()
            return

        # Join group and accept
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Update online status
        self.participant.is_online = True
        await self.participant.asave(update_fields=["is_online"])

        # Broadcast presence
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence.update",
                "participant": self._serialize_participant(self.participant),
                "is_online": True,
            },
        )

    # -------------------------------------------------------------- disconnect

    async def disconnect(self, code):
        """Leave group, update offline status, broadcast."""
        if not hasattr(self, "participant") or self.participant is None:
            return

        # Update offline status
        self.participant.is_online = False
        self.participant.last_seen = timezone.now()
        await self.participant.asave(update_fields=["is_online", "last_seen"])

        # Broadcast presence
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence.update",
                "participant": self._serialize_participant(self.participant),
                "is_online": False,
            },
        )

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ----------------------------------------------------------------- receive

    async def receive(self, text_data=None, bytes_data=None):
        """Dispatch incoming messages by type."""
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        msg_type = data.get("type")
        handlers = {
            "message.send": self._handle_message_send,
            "message.edit": self._handle_message_edit,
            "typing.start": self._handle_typing_start,
            "typing.stop": self._handle_typing_stop,
            "mark_read": self._handle_mark_read,
        }

        handler = handlers.get(msg_type)
        if handler is None:
            await self._send_error(f"Unknown message type: {msg_type}")
            return

        await handler(data)

    # --------------------------------------------------------- message handlers

    async def _handle_message_send(self, data):
        """Create a new message and broadcast to channel group."""
        text = data.get("text", "").strip()
        if not text:
            await self._send_error("Message text is required")
            return

        parent_id = data.get("parent_id")
        parent = None
        if parent_id is not None:
            try:
                parent = await Message.objects.aget(
                    id=parent_id, channel=self.comms_channel
                )
            except Message.DoesNotExist:
                await self._send_error("Parent message not found")
                return

        message = await Message.objects.acreate(
            channel=self.comms_channel,
            sender=self.participant,
            text=text,
            parent=parent,
            attachments=data.get("attachments", []),
            metadata=data.get("metadata", {}),
        )

        serialized = await self._serialize_message(message)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "message.new",
                "message": serialized,
            },
        )

    async def _handle_message_edit(self, data):
        """Edit an existing message (sender only) and broadcast."""
        message_id = data.get("message_id")
        new_text = data.get("text", "").strip()
        if not message_id or not new_text:
            await self._send_error("message_id and text are required")
            return

        try:
            message = await Message.objects.aget(
                id=message_id,
                channel=self.comms_channel,
                sender=self.participant,
            )
        except Message.DoesNotExist:
            await self._send_error("Message not found or not owned by you")
            return

        message.text = new_text
        message.is_edited = True
        message.edited_at = timezone.now()
        await message.asave(update_fields=["text", "is_edited", "edited_at"])

        serialized = await self._serialize_message(message)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "message.edited",
                "message": serialized,
            },
        )

    async def _handle_typing_start(self, data):
        """Broadcast typing indicator."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "typing.indicator",
                "participant": self._serialize_participant(self.participant),
                "is_typing": True,
            },
        )

    async def _handle_typing_stop(self, data):
        """Broadcast typing stopped."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "typing.indicator",
                "participant": self._serialize_participant(self.participant),
                "is_typing": False,
            },
        )

    async def _handle_mark_read(self, data):
        """Update last_read_at for this participant in this channel."""
        await ChannelMembership.objects.filter(
            channel=self.comms_channel, participant=self.participant
        ).aupdate(last_read_at=timezone.now())

    # ---------------------------------------------------- group message handlers

    async def presence_update(self, event):
        """Forward presence.update to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence.update",
                    "participant": event["participant"],
                    "is_online": event["is_online"],
                }
            )
        )

    async def message_new(self, event):
        """Forward message.new to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message.new",
                    "message": event["message"],
                }
            )
        )

    async def message_edited(self, event):
        """Forward message.edited to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message.edited",
                    "message": event["message"],
                }
            )
        )

    async def typing_indicator(self, event):
        """Forward typing.indicator to connected WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing.indicator",
                    "participant": event["participant"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    # ----------------------------------------------------------------- auth helpers

    async def _resolve_participant(self):
        """Resolve Participant from token query param or Django session user."""
        # Try agent token auth first (?token=<api_key>)
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token = self._extract_query_param(query_string, "token")
        if token:
            return await self._resolve_agent_participant(token)

        # Fall back to Django session auth
        user = self.scope.get("user")
        if user and user.is_authenticated:
            try:
                return await Participant.objects.aget(
                    user=user, participant_type="user"
                )
            except Participant.DoesNotExist:
                return None

        return None

    async def _resolve_agent_participant(self, token):
        """Look up Participant via APIKey token."""
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = await APIKey.objects.select_related("user").aget(
                key_hash=key_hash, is_active=True
            )
        except APIKey.DoesNotExist:
            return None

        try:
            return await Participant.objects.aget(
                api_key=api_key, participant_type="agent"
            )
        except Participant.DoesNotExist:
            return None

    @staticmethod
    def _extract_query_param(query_string, key):
        """Extract a single query parameter value from a query string."""
        for part in query_string.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k == key:
                    return v
        return None

    # ----------------------------------------------------------------- serializers

    @staticmethod
    def _serialize_participant(participant):
        """Minimal participant dict for WebSocket payloads."""
        return {
            "id": participant.id,
            "display_name": participant.display_name,
            "participant_type": participant.participant_type,
            "avatar_url": participant.avatar_url,
        }

    @staticmethod
    async def _serialize_message(message):
        """Serialize a Message for WebSocket payloads."""
        sender_data = None
        if message.sender_id:
            try:
                sender = await Participant.objects.aget(id=message.sender_id)
                sender_data = {
                    "id": sender.id,
                    "display_name": sender.display_name,
                    "participant_type": sender.participant_type,
                }
            except Participant.DoesNotExist:
                sender_data = None

        return {
            "id": message.id,
            "channel_id": message.channel_id,
            "sender": sender_data,
            "text": message.text,
            "attachments": message.attachments,
            "parent_id": message.parent_id,
            "is_edited": message.is_edited,
            "edited_at": message.edited_at.isoformat() if message.edited_at else None,
            "metadata": message.metadata,
            "created_at": message.created_at.isoformat(),
        }

    # ----------------------------------------------------------------- error helper

    async def _send_error(self, detail):
        """Send error message to the connected client."""
        await self.send(text_data=json.dumps({"type": "error", "detail": detail}))
