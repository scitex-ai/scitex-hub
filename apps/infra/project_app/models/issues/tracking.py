"""
Issue Tracking Models

IssueAssignment - Tracks when users are assigned to issues
IssueEvent - Tracks important events in an issue's lifecycle
"""

from django.contrib.auth.models import User
from django.db import models

from .issue import Issue


class IssueAssignment(models.Model):
    """
    Model for issue assignments.

    Tracks when users are assigned to issues.
    """

    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, related_name="assignments"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="issue_assignments"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issue_assignments_made",
        help_text="User who made the assignment",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("issue", "user")
        ordering = ["assigned_at"]
        verbose_name = "Issue Assignment"
        verbose_name_plural = "Issue Assignments"

    def __str__(self):
        return f"{self.user.username} assigned to {self.issue}"


class IssueEvent(models.Model):
    """
    Model for issue events.

    Tracks important events in an issue's lifecycle (e.g., closed, reopened, labeled).
    """

    EVENT_TYPE_CHOICES = [
        ("created", "Created"),
        ("closed", "Closed"),
        ("reopened", "Reopened"),
        ("assigned", "Assigned"),
        ("unassigned", "Unassigned"),
        ("labeled", "Labeled"),
        ("unlabeled", "Unlabeled"),
        ("milestoned", "Milestoned"),
        ("demilestoned", "Demilestoned"),
        ("referenced", "Referenced"),
        ("mentioned", "Mentioned"),
    ]

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="Issue this event belongs to",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issue_events",
        help_text="User who triggered the event",
    )
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, help_text="Type of event"
    )

    # Event metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event metadata (e.g., label name, assignee username)",
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
        verbose_name = "Issue Event"
        verbose_name_plural = "Issue Events"

    def __str__(self):
        user_name = self.user.username if self.user else "system"
        return f"{self.event_type} on {self.issue} by {user_name}"
