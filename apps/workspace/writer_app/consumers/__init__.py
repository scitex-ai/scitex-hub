"""
WebSocket consumers for SciTeX Writer real-time collaboration.

This module provides the WriterConsumer class which handles:
- User presence (join/leave notifications)
- Section locking
- Real-time text changes via Operational Transform
- Cursor position broadcasting
- Undo/redo coordination
"""

from .base import WriterConsumerBase
from .broadcast import BroadcastMixin
from .database import DatabaseMixin
from .handlers_comments import CommentHandlerMixin
from .handlers_editing import EditingHandlerMixin
from .handlers_undo_redo import UndoRedoHandlerMixin


class WriterConsumer(
    EditingHandlerMixin,
    UndoRedoHandlerMixin,
    CommentHandlerMixin,
    BroadcastMixin,
    DatabaseMixin,
    WriterConsumerBase,
):
    """
    WebSocket consumer for real-time collaborative editing.

    Combines functionality from:
    - WriterConsumerBase: Connection handling and message dispatch
    - EditingHandlerMixin: Text change, cursor, and section lock handlers
    - UndoRedoHandlerMixin: Undo/redo operation handlers
    - CommentHandlerMixin: Comment create/resolve/delete handlers
    - BroadcastMixin: Broadcast event handlers for room notifications
    - DatabaseMixin: Database operations using Django 5.2 async ORM
    """

    pass


__all__ = ["WriterConsumer"]
