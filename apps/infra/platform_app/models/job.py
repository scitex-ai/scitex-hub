import uuid

from django.conf import settings
from django.db import models


class PlatformJob(models.Model):
    """Tracks background job execution for user apps."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_name = models.CharField(max_length=100, db_index=True)
    job_name = models.CharField(max_length=100, db_index=True)
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="platform_jobs",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    params = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    progress_percent = models.IntegerField(default=0)
    progress_message = models.CharField(max_length=200, blank=True, default="")
    celery_task_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.app_name}.{self.job_name}:{self.id} [{self.status}]"
