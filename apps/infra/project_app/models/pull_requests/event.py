"""
Pull Request Event model - tracks PR events (opened, closed, merged, etc.).
"""

from django.db import models
from django.contrib.auth.models import User


class PullRequestEvent(models.Model):
    """
    Model to track PR events (opened, closed, merged, reviewed, etc.).
    """

    EVENT_CHOICES = [
        ("opened", "Opened"),
        ("closed", "Closed"),
        ("reopened", "Reopened"),
        ("merged", "Merged"),
        ("reviewed", "Reviewed"),
        ("comment", "Comment Added"),
        ("commit", "Commit Added"),
        ("label", "Label Changed"),
        ("assignee", "Assignee Changed"),
        ("reviewer", "Reviewer Changed"),
    ]

    pull_request = models.ForeignKey(
        "project_app.PullRequest",
        on_delete=models.CASCADE,
        related_name="events",
        help_text="PR this event belongs to",
    )
    event_type = models.CharField(
        max_length=20, choices=EVENT_CHOICES, help_text="Type of event"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pr_events",
        help_text="User who triggered the event",
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional event metadata"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["pull_request", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]
        verbose_name = "Pull Request Event"
        verbose_name_plural = "Pull Request Events"

    def __str__(self):
        return f"{self.event_type} - PR #{self.pull_request.number} by {self.actor}"
