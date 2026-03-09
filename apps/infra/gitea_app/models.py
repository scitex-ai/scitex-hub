"""
Gitea App Models

Models for Git/GitHub/Gitea integration functionality.
Extracted from workspace_app to resolve model duplication and properly organize Git-specific features.
"""

from django.db import models


class GitFileStatus(models.Model):
    """Model for tracking Git file status within projects"""

    GIT_STATUS_CHOICES = [
        ("untracked", "Untracked"),
        ("modified", "Modified"),
        ("added", "Added"),
        ("deleted", "Deleted"),
        ("renamed", "Renamed"),
        ("copied", "Copied"),
        ("staged", "Staged"),
        ("committed", "Committed"),
    ]

    project = models.ForeignKey(
        "project_app.Project", on_delete=models.CASCADE, related_name="git_files"
    )
    file_path = models.CharField(
        max_length=500, help_text="Relative path from project root"
    )
    git_status = models.CharField(
        max_length=20, choices=GIT_STATUS_CHOICES, default="untracked"
    )
    last_commit_hash = models.CharField(
        max_length=40, blank=True, help_text="SHA of last commit affecting this file"
    )
    last_commit_message = models.CharField(
        max_length=200, blank=True, help_text="Last commit message"
    )
    last_modified_at = models.DateTimeField(auto_now=True)
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    is_binary = models.BooleanField(default=False, help_text="Whether file is binary")

    class Meta:
        unique_together = ("project", "file_path")
        ordering = ["file_path"]
        indexes = [
            models.Index(fields=["project", "git_status"]),
            models.Index(fields=["project", "file_path"]),
        ]
        verbose_name = "Git File Status"
        verbose_name_plural = "Git File Statuses"

    def __str__(self):
        return f"{self.project.name}:{self.file_path} ({self.git_status})"

    def get_status_icon(self):
        """Get FontAwesome icon for git status"""
        icons = {
            "untracked": "fas fa-question-circle text-warning",
            "modified": "fas fa-edit text-primary",
            "added": "fas fa-plus-circle text-success",
            "deleted": "fas fa-trash text-danger",
            "renamed": "fas fa-exchange-alt text-info",
            "copied": "fas fa-copy text-info",
            "staged": "fas fa-check-circle text-success",
            "committed": "fas fa-check text-muted",
        }
        return icons.get(self.git_status, "fas fa-file")

    def get_status_color(self):
        """Get color class for git status"""
        colors = {
            "untracked": "warning",
            "modified": "primary",
            "added": "success",
            "deleted": "danger",
            "renamed": "info",
            "copied": "info",
            "staged": "success",
            "committed": "muted",
        }
        return colors.get(self.git_status, "secondary")
