"""
ChannelMembership model -- tracks which participants belong to which channels.
"""

from django.db import models


class ChannelMembership(models.Model):
    """Tracks which participants belong to which channels."""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    channel = models.ForeignKey(
        "comms_app.Channel",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    participant = models.ForeignKey(
        "comms_app.Participant",
        on_delete=models.CASCADE,
        related_name="channel_memberships",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("channel", "participant")
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.participant} in {self.channel} ({self.role})"
