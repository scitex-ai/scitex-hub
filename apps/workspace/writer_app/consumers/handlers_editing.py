"""
Editing message handlers for WriterConsumer.
Handles text changes, cursor positions, and section locking.
"""

import json
from datetime import datetime


class EditingHandlerMixin:
    """Mixin providing editing-related handler methods for WriterConsumer."""

    async def handle_text_change(self, data):
        """Handle text change from client using OT coordinator."""
        section_id = data.get("section_id")
        operation = data.get("operation")
        version = data.get("version", 0)

        # Submit operation to OT coordinator
        result = await self.ot_coordinator.submit_operation(
            user_id=self.user.id,
            username=self.user.username,
            session_id=self.session.session_id,
            section_id=section_id,
            operation=operation,
            version=version,
        )

        # Send acknowledgment to sender
        await self.send(
            text_data=json.dumps(
                {
                    "type": "operation_submitted",
                    "operation_id": result.get("operation_id"),
                    "status": result.get("status"),
                    "queue_length": result.get("queue_length", 0),
                    "current_version": result.get("current_version", version),
                }
            )
        )

        # Broadcast processed operations to all users
        if result.get("processed"):
            for processed_op in result["processed"]:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "text_change",
                        "section_id": section_id,
                        "operation": operation,
                        "operation_id": processed_op["operation_id"],
                        "user_id": processed_op["user_id"],
                        "version": processed_op["version"],
                        "timestamp": datetime.now().isoformat(),
                        "sender_channel": self.channel_name,
                    },
                )

        # Handle errors
        if result.get("errors"):
            for error in result["errors"]:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "operation_error",
                            "operation_id": error["operation_id"],
                            "error": error["error"],
                        }
                    )
                )

    async def handle_cursor_position(self, data):
        """Handle cursor position update from client."""
        section = data.get("section")
        position = data.get("position")

        # Update session cursor position
        await self.update_cursor_position(section, position)

        # Broadcast to all users in room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "cursor_update",
                "section": section,
                "position": position,
                "user_id": self.user.id,
                "username": self.user.username,
                "sender_channel": self.channel_name,
            },
        )

    async def handle_section_lock(self, data):
        """Handle section lock request from client."""
        section = data.get("section")

        # Check if section is already locked
        is_locked = await self.is_section_locked(section)
        if is_locked:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "lock_failed",
                        "section": section,
                        "message": "Section is already locked by another user",
                    }
                )
            )
            return

        # Lock section
        await self.lock_section(section)

        # Broadcast lock to all users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "section_locked",
                "section": section,
                "user_id": self.user.id,
                "username": self.user.username,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def handle_section_unlock(self, data):
        """Handle section unlock request from client."""
        section = data.get("section")

        # Unlock section
        await self.unlock_section(section)

        # Broadcast unlock to all users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "section_unlocked",
                "section": section,
                "user_id": self.user.id,
                "username": self.user.username,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def handle_operation_ack(self, data):
        """Handle operation acknowledgment from client."""
        operation_id = data.get("operation_id")
        section_id = data.get("section_id")

        result = await self.ot_coordinator.acknowledge_operation(
            operation_id=operation_id, section_id=section_id
        )

        await self.send(text_data=json.dumps({"type": "ack_received", **result}))

    async def handle_queue_status(self, data):
        """Handle queue status request from client."""
        section_id = data.get("section_id")

        status = await self.ot_coordinator.get_queue_status(section_id)

        await self.send(text_data=json.dumps({"type": "queue_status", **status}))
