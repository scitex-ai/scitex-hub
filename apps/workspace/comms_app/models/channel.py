"""
Channel model -- communication rooms (public, private, direct message).
"""

from django.db import models


class Channel(models.Model):
    """A communication room -- like a Slack channel."""

    CHANNEL_TYPES = [
        ("public", "Public"),
        ("private", "Private"),
        ("direct", "Direct Message"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    channel_type = models.CharField(
        max_length=10, choices=CHANNEL_TYPES, default="public"
    )
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comms_channels",
    )
    created_by = models.ForeignKey(
        "comms_app.Participant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_channels",
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["channel_type"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"#{self.name} ({self.get_channel_type_display()})"
