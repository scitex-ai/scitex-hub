"""
Issue Metadata Models

IssueLabel - Labels for categorizing issues
IssueMilestone - Milestones for grouping issues
"""

from django.db import models


class IssueLabel(models.Model):
    """
    Model for issue labels.

    Labels for categorizing issues (e.g., bug, enhancement, documentation).
    """

    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="issue_labels",
        help_text="Project this label belongs to",
    )
    name = models.CharField(
        max_length=100, help_text="Label name (e.g., 'bug', 'enhancement')"
    )
    description = models.TextField(blank=True, help_text="Label description")
    color = models.CharField(
        max_length=7,
        default="#0366d6",
        help_text="Label color (hex code, e.g., #0366d6)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "name")
        ordering = ["name"]
        verbose_name = "Issue Label"
        verbose_name_plural = "Issue Labels"

    def __str__(self):
        return f"{self.name} ({self.project.name})"


class IssueMilestone(models.Model):
    """
    Model for issue milestones.

    Milestones for grouping issues (e.g., v1.0, Sprint 1).
    """

    STATE_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
    ]

    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="issue_milestones",
        help_text="Project this milestone belongs to",
    )
    title = models.CharField(max_length=255, help_text="Milestone title")
    description = models.TextField(blank=True, help_text="Milestone description")
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default="open",
        help_text="Milestone state",
    )

    # Timestamps
    due_date = models.DateTimeField(
        null=True, blank=True, help_text="Milestone due date"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_date", "title"]
        verbose_name = "Issue Milestone"
        verbose_name_plural = "Issue Milestones"

    def __str__(self):
        return f"{self.title} ({self.project.name})"

    @property
    def is_open(self):
        """Check if milestone is open"""
        return self.state == "open"

    @property
    def progress(self):
        """Calculate milestone completion progress"""
        total = self.issues.count()
        if total == 0:
            return 0
        closed = self.issues.filter(state="closed").count()
        return int((closed / total) * 100)
