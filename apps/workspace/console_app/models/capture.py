"""CaptureRequest model for on-site page capture."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class CaptureRequest(models.Model):
    """Tracks pending/completed page capture requests from agents."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("complete", "Complete"),
        ("denied", "Denied"),
        ("expired", "Expired"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    project = models.ForeignKey("project_app.Project", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    filepath = models.CharField(max_length=500, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# EOF
