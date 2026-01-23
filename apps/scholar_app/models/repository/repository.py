"""
Research Data Repository Models

Repository - External data repository definitions (Zenodo, Figshare, etc.)
RepositoryConnection - User credentials for repository access
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Repository(models.Model):
    """Research data repositories (Zenodo, Figshare, Dryad, etc.)"""

    REPOSITORY_TYPES = [
        ("zenodo", "Zenodo"),
        ("figshare", "Figshare"),
        ("dryad", "Dryad"),
        ("harvard_dataverse", "Harvard Dataverse"),
        ("osf", "Open Science Framework"),
        ("mendeley_data", "Mendeley Data"),
        ("institutional", "Institutional Repository"),
        ("custom", "Custom Repository"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("maintenance", "Under Maintenance"),
        ("deprecated", "Deprecated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    repository_type = models.CharField(max_length=30, choices=REPOSITORY_TYPES)
    description = models.TextField(blank=True)

    # API Configuration
    api_base_url = models.URLField()
    api_version = models.CharField(max_length=20, default="v1")
    api_documentation_url = models.URLField(blank=True)

    # Repository metadata
    website_url = models.URLField(blank=True)
    supports_doi = models.BooleanField(default=True)
    supports_versioning = models.BooleanField(default=True)
    supports_private_datasets = models.BooleanField(default=True)
    max_file_size_mb = models.IntegerField(default=50000)  # 50GB default
    max_dataset_size_mb = models.IntegerField(default=50000)

    # Access and features
    requires_authentication = models.BooleanField(default=True)
    supports_metadata_formats = models.JSONField(
        default=list
    )  # ['dublin_core', 'datacite', 'dcat']
    supported_file_formats = models.JSONField(default=list)
    license_options = models.JSONField(default=list)

    # Repository status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    is_open_access = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False
    )  # Default repository for new deposits

    # Usage statistics
    total_deposits = models.IntegerField(default=0)
    active_connections = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["repository_type", "status"]),
            models.Index(fields=["is_default"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_repository_type_display()})"


class RepositoryConnection(models.Model):
    """User's connection credentials to research data repositories"""

    CONNECTION_STATUS = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("invalid", "Invalid"),
        ("suspended", "Suspended"),
        ("pending", "Pending Verification"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="repository_connections"
    )
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="user_connections"
    )

    # Authentication credentials (encrypted)
    api_token = models.CharField(max_length=500, blank=True)
    api_secret = models.CharField(max_length=500, blank=True)
    oauth_token = models.CharField(max_length=500, blank=True)
    oauth_refresh_token = models.CharField(max_length=500, blank=True)
    username = models.CharField(max_length=200, blank=True)

    # Connection metadata
    connection_name = models.CharField(
        max_length=200, help_text="User-defined name for this connection"
    )
    status = models.CharField(
        max_length=20, choices=CONNECTION_STATUS, default="pending"
    )
    last_verified = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # User preferences
    is_default = models.BooleanField(default=False)
    auto_sync_enabled = models.BooleanField(default=True)
    notification_enabled = models.BooleanField(default=True)

    # Usage tracking
    total_deposits = models.IntegerField(default=0)
    total_downloads = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)

    # Error tracking
    last_error = models.TextField(blank=True)
    error_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["user", "repository", "connection_name"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["repository", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.user.username} -> {self.repository.name} ({self.connection_name})"
        )

    def is_active(self):
        """Check if connection is active and not expired"""
        if self.status != "active":
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
