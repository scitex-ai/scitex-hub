"""
Pull Request Review model - allows reviewers to approve, request changes, or comment.
"""

from django.db import models
from django.contrib.auth.models import User


class PullRequestReview(models.Model):
    """
    Model for PR reviews - allows reviewers to approve, request changes, or comment.
    """

    STATE_CHOICES = [
        ("approved", "Approved"),
        ("changes_requested", "Changes Requested"),
        ("commented", "Commented"),
    ]

    pull_request = models.ForeignKey(
        "project_app.PullRequest",
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="PR being reviewed",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pr_reviews",
        help_text="User submitting the review",
    )
    state = models.CharField(
        max_length=20, choices=STATE_CHOICES, help_text="Review state"
    )
    content = models.TextField(
        blank=True, help_text="Review comments (supports Markdown)"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pull_request", "created_at"]),
            models.Index(fields=["reviewer", "created_at"]),
        ]
        verbose_name = "Pull Request Review"
        verbose_name_plural = "Pull Request Reviews"

    def __str__(self):
        return f"{self.reviewer.username} {self.state} PR #{self.pull_request.number}"
