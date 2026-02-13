"""
Resource Tracking Models

ResourceUsage - Track resource usage for billing and monitoring
ProjectService - Track services running for projects
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ResourceUsage(models.Model):
    """Track resource usage for billing and monitoring."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="resource_usage"
    )

    # Resource metrics
    cpu_seconds = models.FloatField(default=0.0)
    memory_mb_hours = models.FloatField(default=0.0)
    storage_gb = models.FloatField(default=0.0)
    network_gb = models.FloatField(default=0.0)

    # Job counts
    code_executions = models.IntegerField(default=0)
    analysis_jobs = models.IntegerField(default=0)
    notebook_runs = models.IntegerField(default=0)

    # Time period
    date = models.DateField()
    month = models.CharField(max_length=7)  # YYYY-MM format

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "month"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class ProjectService(models.Model):
    """Track services (TensorBoard, Jupyter, etc.) running for projects."""

    SERVICE_TYPES = [
        ("tensorboard", "TensorBoard"),
        ("jupyter", "Jupyter Lab"),
        ("mlflow", "MLflow"),
        ("streamlit", "Streamlit"),
        ("custom", "Custom Service"),
    ]

    SERVICE_STATUS = [
        ("starting", "Starting"),
        ("running", "Running"),
        ("stopped", "Stopped"),
        ("error", "Error"),
    ]

    # Service identification
    service_id = models.UUIDField(default=uuid.uuid4, unique=True)
    project = models.ForeignKey(
        "project_app.Project", on_delete=models.CASCADE, related_name="services"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_services"
    )

    # Service details
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    port = models.IntegerField()
    process_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SERVICE_STATUS, default="starting")

    # Optional configuration
    config = models.JSONField(default=dict, blank=True)  # Custom service config

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(default=timezone.now)
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["port"]),
            models.Index(fields=["last_accessed"]),
        ]
        unique_together = [["project", "port"]]

    def __str__(self):
        return f"{self.service_type} on port {self.port} - {self.project.name}"

    @property
    def is_active(self):
        """Check if service is currently active."""
        return self.status in ["starting", "running"]

    @property
    def uptime(self):
        """Calculate service uptime."""
        if self.stopped_at:
            return (self.stopped_at - self.started_at).total_seconds()
        return (timezone.now() - self.started_at).total_seconds()

    def mark_accessed(self):
        """Update last accessed timestamp."""
        self.last_accessed = timezone.now()
        self.save(update_fields=["last_accessed"])


class UserQuota(models.Model):
    """
    Per-user resource quota overrides.

    Default quotas come from environment variables (config/settings/quotas.py).
    This model allows admins to customize quotas for specific users.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="quota")

    # --- SLURM Job Quotas ---
    slurm_max_concurrent_jobs = models.IntegerField(null=True, blank=True)
    slurm_max_queued_jobs = models.IntegerField(null=True, blank=True)
    slurm_max_cpu_hours_daily = models.IntegerField(null=True, blank=True)
    slurm_max_cpu_hours_monthly = models.IntegerField(null=True, blank=True)
    slurm_max_memory_gb_per_job = models.IntegerField(null=True, blank=True)
    slurm_max_runtime_hours = models.IntegerField(null=True, blank=True)
    slurm_allowed_partitions = models.CharField(max_length=200, blank=True)

    # --- Celery Rate Limits ---
    celery_ai_calls_per_minute = models.IntegerField(null=True, blank=True)
    celery_search_per_minute = models.IntegerField(null=True, blank=True)
    celery_compute_per_minute = models.IntegerField(null=True, blank=True)
    celery_pdf_per_hour = models.IntegerField(null=True, blank=True)

    # --- Storage Quotas ---
    storage_total_gb = models.IntegerField(null=True, blank=True)
    storage_project_max_gb = models.IntegerField(null=True, blank=True)
    storage_file_upload_mb = models.IntegerField(null=True, blank=True)

    # --- Project Quotas ---
    max_projects = models.IntegerField(null=True, blank=True)
    max_collaborators_per_project = models.IntegerField(null=True, blank=True)
    max_api_keys = models.IntegerField(null=True, blank=True)

    # --- HTTP Quotas ---
    http_requests_per_minute = models.IntegerField(null=True, blank=True)
    websocket_connections = models.IntegerField(null=True, blank=True)

    # Admin notes
    notes = models.TextField(blank=True, help_text="Admin notes about quota changes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Quota"
        verbose_name_plural = "User Quotas"

    def __str__(self):
        return f"Quota for {self.user.username}"

    def get_effective_quotas(self) -> dict:
        """
        Get effective quotas, merging user overrides with defaults.

        Returns:
            dict: Effective quotas (user overrides take precedence)
        """
        from config.settings.quotas import DEFAULT_USER_QUOTAS

        quotas = DEFAULT_USER_QUOTAS.copy()

        # Override with user-specific values (only if set)
        if self.slurm_max_concurrent_jobs is not None:
            quotas["slurm"]["max_concurrent_jobs"] = self.slurm_max_concurrent_jobs
        if self.slurm_max_queued_jobs is not None:
            quotas["slurm"]["max_queued_jobs"] = self.slurm_max_queued_jobs
        if self.slurm_max_cpu_hours_daily is not None:
            quotas["slurm"]["max_cpu_hours_daily"] = self.slurm_max_cpu_hours_daily
        if self.slurm_max_cpu_hours_monthly is not None:
            quotas["slurm"]["max_cpu_hours_monthly"] = self.slurm_max_cpu_hours_monthly
        if self.slurm_max_memory_gb_per_job is not None:
            quotas["slurm"]["max_memory_gb_per_job"] = self.slurm_max_memory_gb_per_job
        if self.slurm_max_runtime_hours is not None:
            quotas["slurm"]["max_runtime_hours"] = self.slurm_max_runtime_hours
        if self.slurm_allowed_partitions:
            quotas["slurm"]["allowed_partitions"] = self.slurm_allowed_partitions.split(
                ","
            )

        if self.celery_ai_calls_per_minute is not None:
            quotas["celery"]["ai_calls_per_minute"] = self.celery_ai_calls_per_minute
        if self.celery_search_per_minute is not None:
            quotas["celery"]["search_per_minute"] = self.celery_search_per_minute
        if self.celery_compute_per_minute is not None:
            quotas["celery"]["compute_per_minute"] = self.celery_compute_per_minute
        if self.celery_pdf_per_hour is not None:
            quotas["celery"]["pdf_per_hour"] = self.celery_pdf_per_hour

        if self.storage_total_gb is not None:
            quotas["storage"]["total_gb"] = self.storage_total_gb
        if self.storage_project_max_gb is not None:
            quotas["storage"]["project_max_gb"] = self.storage_project_max_gb
        if self.storage_file_upload_mb is not None:
            quotas["storage"]["file_upload_mb"] = self.storage_file_upload_mb

        if self.max_projects is not None:
            quotas["project"]["max_projects"] = self.max_projects
        if self.max_collaborators_per_project is not None:
            quotas["project"]["max_collaborators_per_project"] = (
                self.max_collaborators_per_project
            )
        if self.max_api_keys is not None:
            quotas["project"]["max_api_keys"] = self.max_api_keys

        if self.http_requests_per_minute is not None:
            quotas["http"]["requests_per_minute"] = self.http_requests_per_minute
        if self.websocket_connections is not None:
            quotas["http"]["websocket_connections"] = self.websocket_connections

        return quotas
