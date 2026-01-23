#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/bibtex_models.py

"""
BibTeX Enrichment Models

Models for tracking BibTeX file enrichment jobs.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class BibTeXEnrichmentJob(models.Model):
    """Track BibTeX enrichment jobs for users."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    BROWSER_MODE_CHOICES = [
        ("stealth", "Stealth Mode"),
        ("interactive", "Interactive Mode"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bibtex_jobs",
        null=True,
        blank=True,
    )
    session_key = models.CharField(
        max_length=40, blank=True, null=True, help_text="For visitor users"
    )

    # Input
    input_file = models.FileField(upload_to="bibtex_uploads/%Y/%m/%d/")
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Original filename before upload",
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 hash of input file content for deduplication",
        db_index=True,
    )
    project_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Optional project name for organization",
    )
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bibtex_jobs",
        help_text="Associated project for Gitea integration",
    )

    # Processing parameters
    num_workers = models.IntegerField(default=4, help_text="Number of parallel workers")
    browser_mode = models.CharField(
        max_length=20, choices=BROWSER_MODE_CHOICES, default="stealth"
    )
    use_cache = models.BooleanField(
        default=True, help_text="Use cached metadata if available"
    )

    # Output
    output_file = models.FileField(
        upload_to="bibtex_enriched/%Y/%m/%d/", blank=True, null=True
    )

    # Progress tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_papers = models.IntegerField(default=0)
    processed_papers = models.IntegerField(default=0)
    failed_papers = models.IntegerField(default=0)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)

    # Processing log for real-time updates
    processing_log = models.TextField(
        blank=True, default="", help_text="Real-time processing log shown to user"
    )

    # Results summary
    enrichment_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of enrichments: citations added, IFs found, PDFs downloaded, etc.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["session_key", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        if self.user:
            return f"BibTeX Job #{self.id} - {self.user.username} ({self.status})"
        else:
            return f"BibTeX Job #{self.id} - visitor ({self.status})"

    def get_progress_percentage(self):
        """Calculate progress percentage."""
        if self.total_papers == 0:
            return 0
        return int((self.processed_papers / self.total_papers) * 100)

    def get_duration(self):
        """Get job duration in seconds."""
        if not self.started_at:
            return None

        end_time = self.completed_at or timezone.now()
        return (end_time - self.started_at).total_seconds()

    def get_duration_display(self):
        """Get human-readable duration."""
        duration = self.get_duration()
        if duration is None:
            return "Not started"

        if duration < 60:
            return f"{int(duration)} seconds"
        elif duration < 3600:
            return f"{int(duration / 60)} minutes"
        else:
            return f"{duration / 3600:.1f} hours"


# EOF
