"""
Participant model -- polymorphic identity for human users and AI agents.
"""

from django.contrib.auth.models import User
from django.db import models


class Participant(models.Model):
    """First-class communication identity -- human user or agent."""

    PARTICIPANT_TYPES = [
        ("user", "Human User"),
        ("agent", "AI Agent"),
    ]

    participant_type = models.CharField(max_length=10, choices=PARTICIPANT_TYPES)

    # For human users (nullable, set when participant_type == "user")
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comms_participant",
    )

    # For agents
    agent_name = models.CharField(max_length=100, blank=True)
    agent_description = models.TextField(blank=True)
    api_key = models.ForeignKey(
        "accounts_app.APIKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comms_participants",
    )

    display_name = models.CharField(max_length=100)
    avatar_url = models.URLField(blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_name"]
        constraints = [
            models.CheckConstraint(
                # Django 5.1+ renamed `check` → `condition`. The keyword
                # was previously accepted alongside `check`; in 5.2 it
                # raises TypeError.
                condition=(
                    models.Q(participant_type="user", user__isnull=False)
                    | models.Q(participant_type="agent", user__isnull=True)
                ),
                name="participant_type_user_xor_agent",
            ),
        ]
        indexes = [
            models.Index(fields=["participant_type"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.get_participant_type_display()})"
