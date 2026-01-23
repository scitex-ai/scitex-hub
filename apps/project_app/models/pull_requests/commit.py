"""
Pull Request Commit model - tracks commits included in a PR.
"""

from django.db import models


class PullRequestCommit(models.Model):
    """
    Model to track commits included in a PR.
    """

    pull_request = models.ForeignKey(
        "project_app.PullRequest",
        on_delete=models.CASCADE,
        related_name="commits",
        help_text="PR this commit belongs to",
    )
    commit_hash = models.CharField(max_length=40, help_text="Git commit SHA")
    commit_message = models.TextField(help_text="Commit message")
    author_name = models.CharField(max_length=255, help_text="Git author name")
    author_email = models.CharField(max_length=255, help_text="Git author email")
    committed_at = models.DateTimeField(help_text="Git commit timestamp")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("pull_request", "commit_hash")
        ordering = ["committed_at"]
        indexes = [
            models.Index(fields=["pull_request", "committed_at"]),
            models.Index(fields=["commit_hash"]),
        ]
        verbose_name = "Pull Request Commit"
        verbose_name_plural = "Pull Request Commits"

    def __str__(self):
        return f"{self.commit_hash[:7]} - {self.commit_message[:50]}"
