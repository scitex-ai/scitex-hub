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
from .handlers_editing import EditingHandlerMixin
from .handlers_undo_redo import UndoRedoHandlerMixin
from .broadcast import BroadcastMixin
from .database import DatabaseMixin


class WriterConsumer(
    EditingHandlerMixin,
    UndoRedoHandlerMixin,
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
    - BroadcastMixin: Broadcast event handlers for room notifications
    - DatabaseMixin: Database operations using Django 5.2 async ORM
    """

    pass


__all__ = ["WriterConsumer"]
