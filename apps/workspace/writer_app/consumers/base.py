"""
Base WebSocket consumer for SciTeX Writer real-time collaboration.
Uses Django 5.2 async ORM for optimal performance.
"""

from channels.generic.websocket import AsyncWebsocketConsumer
import json
from datetime import datetime
from ..models import Manuscript, CollaborativeSession
from ..services.ot_coordinator import OTCoordinator, CollaborativeUndoRedoCoordinator
from scitex import logging

logger = logging.getLogger(__name__)


class WriterConsumerBase(AsyncWebsocketConsumer):
    """
    Base WebSocket consumer for real-time collaborative editing.

    Handles:
    - Connection setup and teardown
    - User presence (join/leave notifications)
    """

    async def connect(self):
        """Handle new WebSocket connection."""
        self.manuscript_id = self.scope["url_route"]["kwargs"]["manuscript_id"]
        self.room_group_name = f"manuscript_{self.manuscript_id}"
        self.user = self.scope["user"]

        # Reject visitor users
        if not self.user.is_authenticated:
            await self.close()
            return

        # Django 5.2 async ORM: Check manuscript access
        try:
            self.manuscript = await Manuscript.objects.select_related(
                "owner", "project"
            ).aget(id=self.manuscript_id)
        except Manuscript.DoesNotExist:
            await self.close()
            return

        # Check permissions
        has_access = await self.check_access()
        if not has_access:
            await self.close()
            return

        # Initialize OT coordinator and undo/redo coordinator for this manuscript
        self.ot_coordinator = OTCoordinator(self.manuscript_id)
        self.undo_redo_coordinator = CollaborativeUndoRedoCoordinator(
            self.manuscript_id
        )

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Create or update collaborative session
        self.session = await self.create_session()

        # Broadcast user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user_id": self.user.id,
                "username": self.user.username,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Send current collaborators list to new user
        collaborators = await self.get_active_collaborators()
        await self.send(
            text_data=json.dumps(
                {"type": "collaborators_list", "collaborators": collaborators}
            )
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        # End session
        if hasattr(self, "session"):
            await self.end_session()

        # Broadcast user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_left",
                "user_id": self.user.id,
                "username": self.user.username,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages - dispatches to handlers."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            handler_name = f"handle_{message_type}"
            if hasattr(self, handler_name):
                await getattr(self, handler_name)(data)
            else:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )
                )

        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Invalid JSON"})
            )
        except Exception as e:
            await self.send(text_data=json.dumps({"type": "error", "message": str(e)}))
