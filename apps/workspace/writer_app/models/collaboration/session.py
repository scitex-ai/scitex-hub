"""Collaboration models for writer_app."""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid


class WriterPresence(models.Model):
    """
    Simple presence tracking for showing who's online and which section they're editing.
    Uses polling (not WebSocket) for simplicity.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="writer_presences"
    )
    project = models.ForeignKey(
        "project_app.Project", on_delete=models.CASCADE, related_name="writer_presences"
    )
    current_section = models.CharField(
        max_length=100, blank=True
    )  # e.g., "manuscript/abstract"
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "project")
        indexes = [
            models.Index(fields=["project", "is_active", "last_seen"]),
        ]
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.user.username} in {self.project.slug} ({self.current_section})"

    @classmethod
    def get_active_users(cls, project_id, minutes=2):
        """Get users active in the last N minutes."""
        threshold = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            project_id=project_id, is_active=True, last_seen__gte=threshold
        ).select_related("user")


class CollaborativeSession(models.Model):
    """Track collaborative editing sessions for real-time collaboration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="collaborative_sessions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="writing_sessions"
    )

    # Session details
    session_id = models.CharField(max_length=100)  # WebSocket session identifier
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # Collaboration features
    locked_sections = models.JSONField(
        default=list, blank=True
    )  # List of section IDs locked by this user
    cursor_position = models.JSONField(
        default=dict, blank=True
    )  # Current cursor position

    # Statistics
    characters_typed = models.IntegerField(default=0)
    operations_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity"]
        unique_together = ["manuscript", "user", "session_id"]

    def __str__(self):
        return f"{self.user.username} - {self.manuscript.title[:30]} ({self.session_id[:8]})"

    @property
    def session_duration(self):
        """Calculate session duration."""
        end_time = self.ended_at or timezone.now()
        return end_time - self.started_at

    def is_session_active(self):
        """Check if session is still active (within 5 minutes of last activity)."""
        if not self.is_active:
            return False
        return timezone.now() - self.last_activity < timedelta(minutes=5)
