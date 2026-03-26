"""
WebSocket message handlers for comment/annotation operations.
Handles incoming comment actions and broadcasts to room.
"""

import json
from datetime import datetime

from ..models import Comment, Manuscript


class CommentHandlerMixin:
    """Mixin providing comment-related WebSocket message handlers."""

    async def handle_comment_create(self, data):
        """Handle new comment creation via WebSocket.

        Expected data:
            {
                "type": "comment_create",
                "section_id": "manuscript/methods",
                "line_start": 10,
                "line_end": 15,
                "text": "Needs citation here.",
                "parent_id": null
            }
        """
        try:
            comment = await Comment.objects.acreate(
                manuscript_id=self.manuscript_id,
                author=self.user,
                section_id=data["section_id"],
                line_start=data["line_start"],
                line_end=data["line_end"],
                text=data["text"],
                parent_id=data.get("parent_id"),
            )

            # Refresh to get author relation for to_dict
            comment = await Comment.objects.select_related("author").aget(id=comment.id)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "comment_created",
                    "comment": comment.to_dict(),
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": f"Failed to create comment: {e}"}
                )
            )

    async def handle_comment_resolve(self, data):
        """Handle comment resolution via WebSocket.

        Expected data:
            {
                "type": "comment_resolve",
                "comment_id": 42
            }
        """
        try:
            comment = await Comment.objects.aget(
                id=data["comment_id"],
                manuscript_id=self.manuscript_id,
                parent__isnull=True,
            )
            comment.status = "resolved"
            await comment.asave(update_fields=["status", "updated_at"])

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "comment_resolved",
                    "comment_id": comment.id,
                    "resolved_by": self.user.username,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Comment.DoesNotExist:
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Comment not found"})
            )

    async def handle_comment_delete(self, data):
        """Handle comment deletion via WebSocket.

        Expected data:
            {
                "type": "comment_delete",
                "comment_id": 42
            }
        """
        try:
            comment = await Comment.objects.aget(
                id=data["comment_id"],
                manuscript_id=self.manuscript_id,
            )

            # Permission check: author or manuscript owner
            manuscript = await Manuscript.objects.aget(id=self.manuscript_id)
            if (
                comment.author_id != self.user.id
                and manuscript.owner_id != self.user.id
            ):
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": "Permission denied"}
                    )
                )
                return

            comment_id = comment.id
            await comment.adelete()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "comment_deleted",
                    "comment_id": comment_id,
                    "deleted_by": self.user.username,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Comment.DoesNotExist:
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Comment not found"})
            )
