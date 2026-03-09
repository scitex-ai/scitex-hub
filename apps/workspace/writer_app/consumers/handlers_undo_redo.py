"""
Undo/redo message handlers for WriterConsumer.
Handles undo, redo, and undo status operations.
"""

import json
from datetime import datetime


class UndoRedoHandlerMixin:
    """Mixin providing undo/redo handler methods for WriterConsumer."""

    async def handle_undo(self, data):
        """Handle undo request from client."""
        section_id = data.get("section_id")
        current_version = data.get("version", 0)

        # Get undo/redo manager for this user and section
        manager = self.undo_redo_coordinator.get_manager(self.user.id, section_id)

        # Perform undo
        undo_result = await manager.undo(current_version)

        if undo_result:
            # Submit the inverse operation through OT coordinator
            result = await self.ot_coordinator.submit_operation(
                user_id=self.user.id,
                username=self.user.username,
                session_id=self.session.session_id,
                section_id=section_id,
                operation=undo_result["operation"],
                version=current_version,
            )

            await self.send(
                text_data=json.dumps(
                    {
                        "type": "undo_result",
                        "success": True,
                        "operation_id": result.get("operation_id"),
                        **undo_result,
                    }
                )
            )

            # Broadcast undo to other users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_undone",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "section_id": section_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        else:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "undo_result",
                        "success": False,
                        "message": "Nothing to undo",
                    }
                )
            )

    async def handle_redo(self, data):
        """Handle redo request from client."""
        section_id = data.get("section_id")
        current_version = data.get("version", 0)

        # Get undo/redo manager for this user and section
        manager = self.undo_redo_coordinator.get_manager(self.user.id, section_id)

        # Perform redo
        redo_result = await manager.redo(current_version)

        if redo_result:
            # Submit the operation through OT coordinator
            result = await self.ot_coordinator.submit_operation(
                user_id=self.user.id,
                username=self.user.username,
                session_id=self.session.session_id,
                section_id=section_id,
                operation=redo_result["operation"],
                version=current_version,
            )

            await self.send(
                text_data=json.dumps(
                    {
                        "type": "redo_result",
                        "success": True,
                        "operation_id": result.get("operation_id"),
                        **redo_result,
                    }
                )
            )

            # Broadcast redo to other users
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_redone",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "section_id": section_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        else:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "redo_result",
                        "success": False,
                        "message": "Nothing to redo",
                    }
                )
            )

    async def handle_undo_status(self, data):
        """Handle undo/redo status request from client."""
        section_id = data.get("section_id")

        # Get undo/redo manager for this user and section
        manager = self.undo_redo_coordinator.get_manager(self.user.id, section_id)

        # Get status
        status = await manager.get_status()

        await self.send(
            text_data=json.dumps(
                {"type": "undo_status", "section_id": section_id, **status}
            )
        )
