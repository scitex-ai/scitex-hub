"""
Issue Metadata Models

IssueLabel - Labels for categorizing issues
IssueMilestone - Milestones for grouping issues
IssueTemplate - Templates for creating issues (Bug Report, Feature Request, etc.)
"""

from django.db import models


class IssueTemplate(models.Model):
    """
    Model for issue templates (like GitHub's ISSUE_TEMPLATE).

    Templates help users create well-structured issues by providing
    pre-filled content and guidance (e.g., Bug Report, Feature Request).
    """

    # Built-in template types
    TEMPLATE_TYPES = [
        ("bug", "Bug Report"),
        ("feature", "Feature Request"),
        ("docs", "Documentation Issue"),
        ("question", "Question"),
        ("custom", "Custom"),
    ]

    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="issue_templates",
        help_text="Project this template belongs to",
    )
    name = models.CharField(
        max_length=100, help_text="Template name (e.g., 'Bug Report')"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short description shown in template selector",
    )
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        default="custom",
        help_text="Template type for default styling",
    )
    icon = models.CharField(
        max_length=50,
        default="fa-file-alt",
        help_text="FontAwesome icon class (e.g., 'fa-bug', 'fa-lightbulb')",
    )
    title_prefix = models.CharField(
        max_length=50,
        blank=True,
        help_text="Prefix for issue title (e.g., '[BUG]', '[FEATURE]')",
    )
    body_template = models.TextField(
        blank=True,
        help_text="Markdown template for issue body",
    )
    labels = models.ManyToManyField(
        "IssueLabel",
        related_name="templates",
        blank=True,
        help_text="Labels to auto-apply when using this template",
    )

    # Display order
    order = models.IntegerField(default=0, help_text="Display order in selector")
    is_active = models.BooleanField(default=True, help_text="Show in template selector")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ("project", "name")
        verbose_name = "Issue Template"
        verbose_name_plural = "Issue Templates"

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    @classmethod
    def get_default_templates(cls):
        """Return default template configurations for new projects."""
        return [
            {
                "name": "Bug Report",
                "description": "Report a bug or unexpected behavior",
                "template_type": "bug",
                "icon": "fa-bug",
                "title_prefix": "[BUG]",
                "order": 1,
                "body_template": """## What's Wrong?
Describe what's happening that shouldn't be.

## Expected Behavior
What should happen instead?

## Steps to Reproduce
1.
2.
3.

## Environment
- Browser:
- OS:

## Additional Context
Add any other context, screenshots, or error messages.
""",
            },
            {
                "name": "Feature Request",
                "description": "Suggest a new feature or enhancement",
                "template_type": "feature",
                "icon": "fa-lightbulb",
                "title_prefix": "[FEATURE]",
                "order": 2,
                "body_template": """## Problem Statement
What problem does this feature solve?

## Proposed Solution
Describe your proposed solution.

## Alternatives Considered
What alternatives have you considered?

## Additional Context
Add any other context, mockups, or examples.
""",
            },
            {
                "name": "Documentation Issue",
                "description": "Report missing, unclear, or incorrect documentation",
                "template_type": "docs",
                "icon": "fa-book",
                "title_prefix": "[DOCS]",
                "order": 3,
                "body_template": """## Documentation Location
Link or describe where the documentation issue is.

## What's Wrong?
Describe what's missing, unclear, or incorrect.

## Suggested Improvement
How should the documentation be improved?
""",
            },
        ]


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
