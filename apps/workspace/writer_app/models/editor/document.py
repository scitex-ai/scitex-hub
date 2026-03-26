"""
Minimal Manuscript model - Writer functionality is in scitex.writer.Writer.

This model exists only for:
1. User/project linking
2. UI metadata (display name, description)
3. Tracking which projects have writer enabled
"""

from pathlib import Path

from django.contrib.auth.models import User
from django.db import models


class Manuscript(models.Model):
    """Minimal manuscript model - delegates to scitex.writer.Writer."""

    # Links to project
    project = models.OneToOneField(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="manuscript",
        null=True,
        blank=True,
        help_text="Project this manuscript belongs to",
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="manuscripts",
        help_text="User who owns this manuscript",
    )

    # Metadata for UI
    title = models.CharField(
        max_length=500,
        default="Untitled Manuscript",
        help_text="Display title (informational only)",
    )

    description = models.TextField(
        blank=True, help_text="Short description of the manuscript"
    )

    # Collaboration
    collaborators = models.ManyToManyField(
        User,
        related_name="collaborated_manuscripts",
        blank=True,
        help_text="Users who can collaborate on this manuscript",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Manuscript"
        verbose_name_plural = "Manuscripts"

    def __str__(self):
        return self.title

    def get_writer_path(self) -> Path:
        """Get path to writer directory for this project."""
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(self.owner)
        project_root = manager.get_project_root_path(self.project)
        if project_root is None:
            return None
        return project_root / "scitex" / "writer"

    @property
    def writer_initialized(self) -> bool:
        """Check if Writer project exists."""
        path = self.get_writer_path()
        if path is None:
            return False
        return (path / "01_manuscript").exists()
