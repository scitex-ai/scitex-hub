#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkflowJob model for SciTeX Projects

Single job within a workflow run.
A workflow can have multiple jobs that run sequentially or in parallel.
"""

from django.db import models


class WorkflowJob(models.Model):
    """
    Single job within a workflow run
    A workflow can have multiple jobs that run sequentially or in parallel
    """

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    run = models.ForeignKey(
        "project_app.WorkflowRun",
        on_delete=models.CASCADE,
        related_name="jobs",
        help_text="Associated workflow run",
    )
    name = models.CharField(max_length=200, help_text="Job name from workflow YAML")
    job_id = models.CharField(
        max_length=100, help_text="Job identifier from workflow YAML"
    )

    # Job configuration
    runs_on = models.CharField(
        max_length=100,
        default="ubuntu-latest",
        help_text="Runner environment (e.g., ubuntu-latest, python:3.11)",
    )
    depends_on = models.JSONField(
        default=list, help_text="List of job IDs that must complete before this job"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued",
        help_text="Current job status",
    )
    conclusion = models.CharField(
        max_length=20, blank=True, help_text="Job conclusion (success, failure, etc.)"
    )

    # Timing
    started_at = models.DateTimeField(null=True, blank=True, help_text="Job start time")
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Job completion time"
    )
    duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="Job duration in seconds"
    )

    # Execution
    runner_id = models.CharField(
        max_length=100, blank=True, help_text="ID of the runner that executed this job"
    )
    container_id = models.CharField(
        max_length=100, blank=True, help_text="Container ID for this job execution"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Matrix configuration (for matrix jobs)
    matrix_config = models.JSONField(
        default=dict,
        help_text="Matrix configuration for this job (e.g., {python: '3.11', os: 'ubuntu'})",
    )

    class Meta:
        app_label = "project_app"
        unique_together = ("run", "job_id")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["run", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.run} - {self.name}"

    def calculate_duration(self):
        """Calculate and update duration"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
            self.save(update_fields=["duration_seconds"])


# EOF
