#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkflowArtifact model for SciTeX Projects

Files/artifacts produced by workflow runs (similar to GitHub Actions artifacts).
"""

from django.db import models
from django.utils import timezone


class WorkflowArtifact(models.Model):
    """
    Files/artifacts produced by workflow runs
    Similar to GitHub Actions artifacts
    """

    run = models.ForeignKey(
        "project_app.WorkflowRun",
        on_delete=models.CASCADE,
        related_name="artifacts",
        help_text="Associated workflow run",
    )
    name = models.CharField(max_length=200, help_text="Artifact name")
    file_path = models.CharField(max_length=500, help_text="Path to artifact file")
    file_size = models.BigIntegerField(default=0, help_text="Artifact size in bytes")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Artifact expiration time")

    class Meta:
        app_label = "project_app"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["run", "created_at"]),
        ]

    def __str__(self):
        return f"{self.run} - {self.name}"

    def is_expired(self):
        """Check if artifact is expired"""
        return timezone.now() > self.expires_at


# EOF
