"""
Message model -- a single message in a channel, with optional threading.
"""

from django.db import models


class Message(models.Model):
    """A single message in a channel, with optional threading."""

    channel = models.ForeignKey(
        "comms_app.Channel",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        "comms_app.Participant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_messages",
    )
    text = models.TextField()
    attachments = models.JSONField(default=list, blank=True)

    # Threading (null = top-level message)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )

    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["channel", "created_at"]),
            models.Index(fields=["parent", "created_at"]),
        ]

    def __str__(self):
        sender_name = self.sender.display_name if self.sender else "[deleted]"
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"{sender_name}: {preview}"
