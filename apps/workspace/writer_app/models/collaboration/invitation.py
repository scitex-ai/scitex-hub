"""CollaborationInvitation model for managing manuscript collaboration invites."""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class CollaborationInvitation(models.Model):
    """Track invitations for collaborative manuscript editing."""

    ROLE_CHOICES = [
        ("viewer", "Viewer"),
        ("editor", "Editor"),
        ("admin", "Admin"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "writer_app.Manuscript",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_collaboration_invites",
    )
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="received_collaboration_invites",
    )
    invited_email = models.EmailField(
        blank=True,
        help_text="For inviting users not yet registered",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="editor")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(blank=True, help_text="Optional invitation message")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [
            ("manuscript", "invited_user"),
            ("manuscript", "invited_email"),
        ]
        indexes = [
            models.Index(fields=["manuscript", "status"]),
            models.Index(fields=["invited_user", "status"]),
        ]

    def __str__(self):
        invitee = (
            self.invited_user.username if self.invited_user else self.invited_email
        )
        return f"Invitation to {invitee} for {self.manuscript.title[:30]}"

    def accept(self):
        """Accept the invitation and add user as collaborator."""
        self.status = "accepted"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at", "updated_at"])
        # Add user to manuscript collaborators
        if self.invited_user:
            self.manuscript.collaborators.add(self.invited_user)

    def decline(self):
        """Decline the invitation."""
        self.status = "declined"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at", "updated_at"])

    def cancel(self):
        """Cancel the invitation."""
        self.status = "cancelled"
        self.save(update_fields=["status", "updated_at"])
