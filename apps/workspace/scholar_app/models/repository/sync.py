"""
Repository Synchronization Models

RepositorySync - Track synchronization operations with repositories
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .dataset import Dataset
from .repository import RepositoryConnection


class RepositorySync(models.Model):
    """Track synchronization operations with repositories"""

    SYNC_TYPES = [
        ("upload", "Upload to Repository"),
        ("download", "Download from Repository"),
        ("metadata_update", "Update Metadata"),
        ("status_check", "Status Check"),
        ("full_sync", "Full Synchronization"),
    ]

    SYNC_STATUS = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Sync target
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="repository_syncs"
    )
    repository_connection = models.ForeignKey(
        RepositoryConnection, on_delete=models.CASCADE, related_name="syncs"
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="syncs", null=True, blank=True
    )

    # Sync details
    sync_type = models.CharField(max_length=30, choices=SYNC_TYPES)
    status = models.CharField(max_length=20, choices=SYNC_STATUS, default="pending")

    # Progress tracking
    total_items = models.IntegerField(default=0)
    completed_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)
    total_bytes = models.BigIntegerField(default=0)
    transferred_bytes = models.BigIntegerField(default=0)

    # Results and logs
    result_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    sync_log = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["repository_connection", "sync_type"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        target = self.dataset.title if self.dataset else "Repository"
        return f"{self.get_sync_type_display()}: {target} ({self.status})"

    def get_progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0
        return (self.completed_items / self.total_items) * 100

    def get_transfer_speed(self):
        """Calculate transfer speed in bytes per second"""
        if not self.started_at or self.transferred_bytes == 0:
            return 0

        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        else:
            duration = (timezone.now() - self.started_at).total_seconds()

        if duration > 0:
            return self.transferred_bytes / duration
        return 0
