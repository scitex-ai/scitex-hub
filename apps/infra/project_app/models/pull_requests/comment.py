"""
Pull Request Comment model - supports both general and inline code comments.
"""

from django.db import models
from django.contrib.auth.models import User


class PullRequestComment(models.Model):
    """
    Model for PR comments - supports both general and inline code comments.
    """

    pull_request = models.ForeignKey(
        "project_app.PullRequest",
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="PR this comment belongs to",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pr_comments",
        help_text="User who wrote the comment",
    )
    content = models.TextField(help_text="Comment content (supports Markdown)")

    # Inline comment fields (optional - null for general comments)
    file_path = models.CharField(
        max_length=500, blank=True, help_text="File path for inline comments"
    )
    line_number = models.IntegerField(
        null=True, blank=True, help_text="Line number for inline comments"
    )
    commit_sha = models.CharField(
        max_length=40, blank=True, help_text="Commit SHA for inline comments"
    )

    # Comment threading
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent comment for threaded discussions",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited = models.BooleanField(default=False)

    # Review association
    review = models.ForeignKey(
        "project_app.PullRequestReview",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
        help_text="Review this comment is part of (optional)",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["pull_request", "created_at"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["file_path", "line_number"]),
        ]
        verbose_name = "Pull Request Comment"
        verbose_name_plural = "Pull Request Comments"

    def __str__(self):
        if self.file_path:
            return f"Comment by {self.author.username} on {self.file_path}:{self.line_number}"
        return f"Comment by {self.author.username} on PR #{self.pull_request.number}"

    @property
    def is_inline(self):
        """Check if this is an inline code comment"""
        return bool(self.file_path and self.line_number)

    @property
    def is_general(self):
        """Check if this is a general comment"""
        return not self.is_inline
