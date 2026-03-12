"""
Code Execution Models

CodeExecutionJob - Track code execution jobs with security and resource monitoring
DataAnalysisJob - Specialized model for data analysis tasks using MNGS
"""

import uuid

from django.contrib.auth.models import User
from django.db import models


class CodeExecutionJob(models.Model):
    """Track code execution jobs with security and resource monitoring."""

    JOB_STATUS = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("timeout", "Timeout"),
        ("cancelled", "Cancelled"),
    ]

    EXECUTION_TYPES = [
        ("script", "Python Script"),
        ("notebook", "Jupyter Notebook"),
        ("analysis", "Data Analysis"),
        ("mngs", "MNGS Function Call"),
    ]

    # Job identification
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="code_jobs")

    # Code and execution
    execution_type = models.CharField(
        max_length=20, choices=EXECUTION_TYPES, default="script"
    )
    source_code = models.TextField()
    requirements = models.TextField(blank=True)  # pip requirements

    # Job status and results
    status = models.CharField(max_length=20, choices=JOB_STATUS, default="queued")
    output = models.TextField(blank=True)
    error_output = models.TextField(blank=True)
    return_code = models.IntegerField(null=True, blank=True)

    # Resource usage tracking
    cpu_time = models.FloatField(null=True, blank=True)  # CPU seconds
    memory_peak = models.BigIntegerField(null=True, blank=True)  # Peak memory in bytes
    execution_time = models.FloatField(
        null=True, blank=True
    )  # Wall clock time in seconds

    # Security and limits
    timeout_seconds = models.IntegerField(default=300)  # 5 minute default timeout
    max_memory_mb = models.IntegerField(default=512)  # 512MB default limit
    max_cpu_time = models.IntegerField(default=180)  # 3 minutes CPU time

    # File outputs
    output_files = models.JSONField(default=list)  # List of output file paths
    plot_files = models.JSONField(default=list)  # Generated plots/figures

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"CodeJob {self.job_id} ({self.status})"

    @property
    def duration(self):
        """Calculate job duration if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def save(self, *args, **kwargs):
        """Override save to trigger integrations on completion."""
        is_newly_completed = (
            self.pk
            and self.status == "completed"
            and CodeExecutionJob.objects.filter(pk=self.pk, status="completed").count()
            == 0
        )

        super().save(*args, **kwargs)

        # Trigger integrations for newly completed jobs
        if is_newly_completed:
            if self.plot_files or self.output_files:
                self._sync_to_viz_module()

            # Trigger repository sync if enabled
            self._sync_to_repository()

    def _sync_to_viz_module(self):
        """Sync completed job to Viz module."""
        try:
            from apps.workspace.figrecipe_app.code_integration import (
                auto_sync_code_completion,
            )

            result = auto_sync_code_completion(self)

            # Update job with sync results
            if result.get("data_source_created"):
                self.output += (
                    f"\n\nViz Integration: Created data source and "
                    f"{result.get('visualizations_created', 0)} visualizations"
                )
                super().save(update_fields=["output"])

        except Exception as e:
            # Log error but don't fail the job
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to sync code job {self.job_id} to Viz module: {e}")

    def _sync_to_repository(self):
        """Sync completed job to data repository."""
        try:
            from ..repository_integration import auto_sync_code_completion

            result = auto_sync_code_completion(self)

            # Update job with sync results
            if result.get("auto_sync"):
                sync_info = (
                    f"\n\nRepository Sync: Created dataset "
                    f"'{result.get('dataset_title')}' in {result.get('repository_name')}"
                )
                sync_info += f"\nFiles synced: {result.get('files_synced', 0)}"
                sync_info += f"\nTotal size: {result.get('total_size', 0)} bytes"
                self.output += sync_info
                super().save(update_fields=["output"])

        except Exception as e:
            # Log error but don't fail the job
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to sync code job {self.job_id} to repository: {e}")


class DataAnalysisJob(models.Model):
    """Specialized model for data analysis tasks using MNGS."""

    ANALYSIS_TYPES = [
        ("time_series", "Time Series Analysis"),
        ("statistics", "Statistical Analysis"),
        ("signal_processing", "Signal Processing"),
        ("machine_learning", "Machine Learning"),
        ("visualization", "Data Visualization"),
        ("custom", "Custom Analysis"),
    ]

    # Job identification
    analysis_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="analysis_jobs"
    )
    code_job = models.OneToOneField(
        CodeExecutionJob, on_delete=models.CASCADE, null=True, blank=True
    )

    # Analysis details
    analysis_type = models.CharField(max_length=30, choices=ANALYSIS_TYPES)
    input_data_path = models.CharField(max_length=500, blank=True)
    parameters = models.JSONField(default=dict)

    # Results
    results = models.JSONField(default=dict)
    summary = models.TextField(blank=True)
    figures_generated = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Analysis {self.analysis_id} ({self.analysis_type})"
