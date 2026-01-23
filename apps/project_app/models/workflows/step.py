#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkflowStep model for SciTeX Projects

Single step within a job. Steps execute sequentially within a job.
"""

from django.db import models


class WorkflowStep(models.Model):
    """
    Single step within a job
    Steps execute sequentially within a job
    """

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    job = models.ForeignKey(
        "project_app.WorkflowJob",
        on_delete=models.CASCADE,
        related_name="steps",
        help_text="Associated job",
    )
    name = models.CharField(max_length=200, help_text="Step name")
    step_number = models.IntegerField(help_text="Step number within job (sequential)")

    # Step configuration
    command = models.TextField(
        help_text="Command to execute (shell command or action reference)"
    )
    working_directory = models.CharField(
        max_length=500, blank=True, help_text="Working directory for this step"
    )
    environment_vars = models.JSONField(
        default=dict, help_text="Environment variables for this step"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued",
        help_text="Current step status",
    )
    conclusion = models.CharField(
        max_length=20, blank=True, help_text="Step conclusion (success, failure, etc.)"
    )

    # Execution results
    output = models.TextField(blank=True, help_text="Step output (stdout)")
    error_output = models.TextField(blank=True, help_text="Step error output (stderr)")
    exit_code = models.IntegerField(
        null=True, blank=True, help_text="Process exit code"
    )

    # Timing
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="Step start time"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Step completion time"
    )
    duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="Step duration in seconds"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Conditional execution
    condition = models.CharField(
        max_length=200,
        blank=True,
        help_text="Condition expression (if: always(), if: failure(), etc.)",
    )
    continue_on_error = models.BooleanField(
        default=False, help_text="Continue job execution even if this step fails"
    )

    class Meta:
        app_label = "project_app"
        unique_together = ("job", "step_number")
        ordering = ["step_number"]
        indexes = [
            models.Index(fields=["job", "step_number"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.job.name} - Step {self.step_number}: {self.name}"

    def calculate_duration(self):
        """Calculate and update duration"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
            self.save(update_fields=["duration_seconds"])

    def append_output(self, text):
        """Append text to output (for streaming logs)"""
        self.output = (self.output or "") + text
        self.save(update_fields=["output"])

    def append_error(self, text):
        """Append text to error output"""
        self.error_output = (self.error_output or "") + text
        self.save(update_fields=["error_output"])


# EOF
