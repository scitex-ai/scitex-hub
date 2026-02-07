"""
Notebook and Code Library Models

Notebook - Jupyter notebook management
CodeLibrary - Reusable code snippets and functions
"""

import uuid

from django.contrib.auth.models import User
from django.db import models


class Notebook(models.Model):
    """Jupyter notebook management."""

    NOTEBOOK_STATUS = [
        ("draft", "Draft"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("shared", "Shared"),
    ]

    # Notebook identification
    notebook_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notebooks")

    # Notebook metadata
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=NOTEBOOK_STATUS, default="draft")

    # Content
    content = models.JSONField(default=dict)  # Jupyter notebook JSON
    file_path = models.CharField(max_length=500, blank=True)

    # Sharing and collaboration
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        User, related_name="shared_notebooks", blank=True
    )

    # Execution tracking
    last_executed = models.DateTimeField(null=True, blank=True)
    execution_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["user", "title"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class CodeLibrary(models.Model):
    """Reusable code snippets and functions."""

    LIBRARY_TYPES = [
        ("function", "Function"),
        ("class", "Class"),
        ("script", "Script"),
        ("template", "Template"),
        ("example", "Example"),
    ]

    # Library identification
    library_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="code_library"
    )

    # Code metadata
    name = models.CharField(max_length=100)
    description = models.TextField()
    library_type = models.CharField(max_length=20, choices=LIBRARY_TYPES)
    tags = models.CharField(max_length=200, blank=True)  # Comma-separated tags

    # Code content
    source_code = models.TextField()
    language = models.CharField(max_length=20, default="python")
    requirements = models.TextField(blank=True)

    # Usage and sharing
    is_public = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    shared_with = models.ManyToManyField(User, related_name="shared_code", blank=True)

    # Version control
    version = models.CharField(max_length=20, default="1.0.0")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.name} ({self.library_type})"
