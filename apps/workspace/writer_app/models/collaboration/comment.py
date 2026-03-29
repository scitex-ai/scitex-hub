"""Comment/annotation model for manuscript review collaboration."""

from django.contrib.auth.models import User
from django.db import models


class Comment(models.Model):
    """
    Inline comment for manuscript review.

    Supports threaded replies (parent FK to self) and status tracking
    for the David-sensei review workflow.
    """

    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    manuscript = models.ForeignKey(
        "writer_app.Manuscript",
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="Manuscript this comment belongs to",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="writer_comments",
        help_text="User who wrote this comment",
    )

    # Location within the manuscript
    section_id = models.CharField(
        max_length=200,
        help_text="Which .tex section this comment targets (e.g. 'manuscript/methods')",
    )
    line_start = models.IntegerField(
        help_text="Starting line number in the section",
    )
    line_end = models.IntegerField(
        help_text="Ending line number in the section",
    )

    # Text-snippet anchoring (survives edits — source of truth for position)
    anchor_text = models.TextField(
        blank=True,
        default="",
        help_text="Verbatim text snippet this comment is anchored to (for re-matching after edits)",
    )
    anchor_context_before = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="~50 chars of text before the anchor (disambiguation)",
    )
    anchor_context_after = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="~50 chars of text after the anchor (disambiguation)",
    )

    # Content
    text = models.TextField(
        help_text="Comment content",
    )

    # Threading
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent comment for reply threads (null for top-level comments)",
    )

    # Status
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="open",
        help_text="Current status of this comment thread",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["section_id", "line_start", "-created_at"]
        indexes = [
            models.Index(fields=["manuscript", "section_id"]),
            models.Index(fields=["manuscript", "status"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        prefix = "Re: " if self.parent else ""
        truncated = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"{prefix}{self.author.username}: {truncated}"

    @property
    def is_reply(self):
        """Whether this comment is a reply to another comment."""
        return self.parent_id is not None

    @property
    def thread_root(self):
        """Get the root comment of this thread."""
        if self.parent is None:
            return self
        return self.parent.thread_root

    @property
    def reply_count(self):
        """Number of replies to this comment."""
        return self.replies.count()

    def to_dict(self):
        """Serialize comment to dict for JSON responses."""
        return {
            "id": self.id,
            "manuscript_id": self.manuscript_id,
            "author": {
                "id": self.author_id,
                "username": self.author.username,
            },
            "section_id": self.section_id,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "anchor_text": self.anchor_text,
            "anchor_context_before": self.anchor_context_before,
            "anchor_context_after": self.anchor_context_after,
            "text": self.text,
            "parent_id": self.parent_id,
            "status": self.status,
            "reply_count": self.reply_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
