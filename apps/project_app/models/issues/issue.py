"""
Core Issue Models

Issue - Main issue tracking model
IssueComment - Issue comments
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Issue(models.Model):
    """
    Model for Issues - GitHub-style issue tracking.

    Represents a bug report, feature request, or general discussion item.
    """

    STATE_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
    ]

    # Core fields
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="issues",
        help_text="Project this issue belongs to",
    )
    number = models.IntegerField(
        help_text="Issue number (auto-incremented per project)"
    )
    title = models.CharField(max_length=255, help_text="Issue title")
    description = models.TextField(
        blank=True, help_text="Issue description (supports Markdown)"
    )

    # Author
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="authored_issues",
        help_text="User who created the issue",
    )

    # State
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default="open",
        db_index=True,
        help_text="Current state of the issue",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Closing information
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_issues",
        help_text="User who closed the issue",
    )

    # Labels and assignees
    labels = models.ManyToManyField(
        "IssueLabel",
        related_name="issues",
        blank=True,
        help_text="Labels assigned to this issue",
    )
    assignees = models.ManyToManyField(
        User,
        through="IssueAssignment",
        through_fields=("issue", "user"),
        related_name="assigned_issues",
        blank=True,
        help_text="Users assigned to this issue",
    )

    # Milestone
    milestone = models.ForeignKey(
        "IssueMilestone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
        help_text="Milestone this issue belongs to",
    )

    # Reactions count (like GitHub)
    reactions_count = models.JSONField(
        default=dict,
        blank=True,
        help_text="Reaction counts (e.g., {'thumbsup': 5, 'heart': 2})",
    )

    class Meta:
        unique_together = ("project", "number")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "state"]),
            models.Index(fields=["project", "number"]),
            models.Index(fields=["author", "created_at"]),
        ]
        verbose_name = "Issue"
        verbose_name_plural = "Issues"

    def __str__(self):
        return f"Issue #{self.number}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-increment issue number per project
        if not self.number:
            last_issue = (
                Issue.objects.filter(project=self.project).order_by("-number").first()
            )
            self.number = (last_issue.number + 1) if last_issue else 1
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        """Check if issue is open"""
        return self.state == "open"

    @property
    def is_closed(self):
        """Check if issue is closed"""
        return self.state == "closed"

    def close(self, user):
        """Close this issue"""
        from .tracking import IssueEvent

        self.state = "closed"
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

        # Create event
        IssueEvent.objects.create(
            issue=self, user=user, event_type="closed", created_at=timezone.now()
        )

    def reopen(self, user):
        """Reopen this issue"""
        from .tracking import IssueEvent

        self.state = "open"
        self.closed_at = None
        self.closed_by = None
        self.save()

        # Create event
        IssueEvent.objects.create(
            issue=self, user=user, event_type="reopened", created_at=timezone.now()
        )


class IssueComment(models.Model):
    """
    Model for issue comments.

    Represents a comment on an issue (similar to GitHub issue comments).
    """

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="Issue this comment belongs to",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="issue_comments",
        help_text="User who wrote the comment",
    )
    content = models.TextField(help_text="Comment content (supports Markdown)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Editing information
    is_edited = models.BooleanField(
        default=False, help_text="Whether comment has been edited"
    )

    # Reactions
    reactions_count = models.JSONField(
        default=dict, blank=True, help_text="Reaction counts"
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue", "created_at"]),
            models.Index(fields=["author", "created_at"]),
        ]
        verbose_name = "Issue Comment"
        verbose_name_plural = "Issue Comments"

    def __str__(self):
        return f"Comment on {self.issue} by {self.author.username}"
