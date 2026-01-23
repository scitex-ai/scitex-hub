#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkflowRun model for SciTeX Projects

Single execution of a workflow (similar to GitHub Actions run)
"""

from django.db import models
from django.contrib.auth.models import User


class WorkflowRun(models.Model):
    """
    Single execution of a workflow (similar to GitHub Actions run)
    """

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    CONCLUSION_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
        ("cancelled", "Cancelled"),
        ("skipped", "Skipped"),
        ("timed_out", "Timed Out"),
    ]

    workflow = models.ForeignKey(
        "project_app.Workflow",
        on_delete=models.CASCADE,
        related_name="runs",
        help_text="Associated workflow",
    )
    run_number = models.IntegerField(
        help_text="Sequential run number for this workflow"
    )

    # Trigger information
    trigger_event = models.CharField(
        max_length=50,
        help_text="Event that triggered this run (push, pull_request, manual, etc.)",
    )
    trigger_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_workflow_runs",
        help_text="User who triggered this run (for manual triggers)",
    )
    trigger_data = models.JSONField(
        default=dict, help_text="Additional trigger data (commit SHA, branch, etc.)"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued",
        help_text="Current run status",
    )
    conclusion = models.CharField(
        max_length=20,
        choices=CONCLUSION_CHOICES,
        blank=True,
        help_text="Final run conclusion",
    )

    # Timing
    started_at = models.DateTimeField(null=True, blank=True, help_text="Run start time")
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Run completion time"
    )
    duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="Run duration in seconds"
    )

    # Git information
    commit_sha = models.CharField(
        max_length=40, blank=True, help_text="Git commit SHA that triggered this run"
    )
    branch = models.CharField(max_length=200, blank=True, help_text="Git branch")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Environment
    environment = models.CharField(
        max_length=100,
        default="default",
        help_text="Environment name (e.g., production, staging, development)",
    )

    class Meta:
        app_label = "project_app"
        unique_together = ("workflow", "run_number")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow", "status"]),
            models.Index(fields=["workflow", "-run_number"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.workflow.name} #{self.run_number}"

    def save(self, *args, **kwargs):
        """Auto-generate run number if not set"""
        if not self.run_number:
            # Get the last run number for this workflow
            last_run = (
                WorkflowRun.objects.filter(workflow=self.workflow)
                .order_by("-run_number")
                .first()
            )
            self.run_number = (last_run.run_number + 1) if last_run else 1

        super().save(*args, **kwargs)

    def calculate_duration(self):
        """Calculate and update duration"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
            self.save(update_fields=["duration_seconds"])

    def get_absolute_url(self):
        """Get run detail URL"""
        from django.urls import reverse

        return reverse(
            "user_projects:workflow_run_detail",
            kwargs={
                "username": self.workflow.project.owner.username,
                "slug": self.workflow.project.slug,
                "run_id": self.id,
            },
        )


# EOF
