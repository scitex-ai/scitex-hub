#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow model for SciTeX Projects

GitHub Actions-style workflow definition (similar to .github/workflows/*.yml)
"""

from django.db import models
from django.contrib.auth.models import User
import yaml


class Workflow(models.Model):
    """
    Workflow definition (similar to .github/workflows/*.yml)
    Stored in .scitex/workflows/ directory of each project
    """

    TRIGGER_EVENT_CHOICES = [
        ("push", "Push"),
        ("pull_request", "Pull Request"),
        ("schedule", "Schedule"),
        ("manual", "Manual"),
        ("issue", "Issue"),
        ("release", "Release"),
    ]

    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="workflows",
        help_text="Associated project",
    )
    name = models.CharField(
        max_length=200, help_text="Workflow name (e.g., 'Python Tests', 'LaTeX Build')"
    )
    file_path = models.CharField(
        max_length=500, help_text="Path to workflow YAML file in .scitex/workflows/"
    )
    description = models.TextField(blank=True, help_text="Workflow description")

    # Workflow configuration
    yaml_content = models.TextField(help_text="YAML workflow definition content")
    trigger_events = models.JSONField(
        default=list, help_text="List of trigger events (push, pull_request, etc.)"
    )
    enabled = models.BooleanField(default=True, help_text="Whether workflow is enabled")

    # Schedule configuration
    schedule_cron = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cron expression for scheduled runs (e.g., '0 0 * * *')",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workflows",
        help_text="User who created this workflow",
    )

    # Statistics
    total_runs = models.IntegerField(default=0, help_text="Total number of runs")
    successful_runs = models.IntegerField(
        default=0, help_text="Number of successful runs"
    )
    failed_runs = models.IntegerField(default=0, help_text="Number of failed runs")
    last_run_at = models.DateTimeField(
        null=True, blank=True, help_text="Last run timestamp"
    )
    last_run_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="Last run status (success, failure, cancelled)",
    )

    class Meta:
        app_label = "project_app"
        unique_together = ("project", "name")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["project", "enabled"]),
            models.Index(fields=["project", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    def parse_yaml(self):
        """Parse YAML content and return Python dict"""
        try:
            return yaml.safe_load(self.yaml_content)
        except yaml.YAMLError as e:
            return {"error": str(e)}

    def get_absolute_url(self):
        """Get workflow detail URL"""
        from django.urls import reverse

        return reverse(
            "user_projects:workflow_detail",
            kwargs={
                "username": self.project.owner.username,
                "slug": self.project.slug,
                "workflow_id": self.id,
            },
        )


# EOF
