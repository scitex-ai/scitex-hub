"""
Pull Request Label model - labels for categorizing PRs.
"""

from django.db import models


class PullRequestLabel(models.Model):
    """
    Model for PR labels (e.g., 'bug', 'enhancement', 'documentation').
    """

    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="pr_labels",
        help_text="Project this label belongs to",
    )
    name = models.CharField(
        max_length=50, help_text="Label name (e.g., 'bug', 'enhancement')"
    )
    color = models.CharField(
        max_length=7, default="#0969da", help_text="Label color (hex code)"
    )
    description = models.TextField(blank=True, help_text="Label description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "name")
        ordering = ["name"]
        verbose_name = "Pull Request Label"
        verbose_name_plural = "Pull Request Labels"

    def __str__(self):
        return self.name
