"""
Research Dataset Models

Dataset - Research datasets stored in repositories
DatasetFile - Individual files within a dataset
DatasetVersion - Version tracking for datasets
"""

import uuid

from django.contrib.auth.models import User
from django.db import models

from .repository import RepositoryConnection


class Dataset(models.Model):
    """Research datasets stored in repositories"""

    DATASET_TYPES = [
        ("raw_data", "Raw Data"),
        ("processed_data", "Processed Data"),
        ("analysis_results", "Analysis Results"),
        ("code_output", "Code Execution Output"),
        ("supplementary", "Supplementary Materials"),
        ("replication_data", "Replication Data"),
        ("metadata", "Metadata Only"),
    ]

    VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
        ("restricted", "Restricted Access"),
        ("embargoed", "Embargoed"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("published", "Published"),
        ("updated", "Updated"),
        ("deprecated", "Deprecated"),
        ("deleted", "Deleted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic metadata
    title = models.CharField(max_length=500)
    description = models.TextField()
    dataset_type = models.CharField(max_length=30, choices=DATASET_TYPES)
    keywords = models.CharField(max_length=500, blank=True)

    # Ownership and collaboration
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_datasets"
    )
    collaborators = models.ManyToManyField(
        User, related_name="shared_datasets", blank=True
    )

    # Repository information
    repository_connection = models.ForeignKey(
        RepositoryConnection, on_delete=models.CASCADE, related_name="datasets"
    )
    repository_id = models.CharField(
        max_length=200, blank=True
    )  # ID in the external repository
    repository_url = models.URLField(blank=True)
    repository_doi = models.CharField(max_length=100, blank=True)

    # Version and status
    version = models.CharField(max_length=50, default="1.0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default="private"
    )

    # File information
    file_count = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    file_formats = models.JSONField(default=list)  # List of file extensions

    # Licensing and access
    license = models.CharField(max_length=200, blank=True)
    access_conditions = models.TextField(blank=True)
    embargo_until = models.DateTimeField(null=True, blank=True)

    # Research context
    related_papers = models.ManyToManyField(
        "SearchIndex", related_name="associated_datasets", blank=True
    )
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="datasets",
    )

    # Code integration
    generated_by_job = models.ForeignKey(
        "console_app.CodeExecutionJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_datasets",
    )
    associated_notebooks = models.ManyToManyField(
        "console_app.Notebook", related_name="associated_datasets", blank=True
    )

    # Manuscript integration
    cited_in_manuscripts = models.ManyToManyField(
        "writer_app.Manuscript", related_name="cited_datasets", blank=True
    )

    # Usage and impact
    download_count = models.IntegerField(default=0)
    citation_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["repository_connection", "status"]),
            models.Index(fields=["dataset_type"]),
            models.Index(fields=["visibility"]),
            models.Index(fields=["-published_at"]),
        ]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def get_file_size_display(self):
        """Return human-readable file size"""
        size_bytes = self.total_size_bytes
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def can_be_edited(self, user):
        """Check if user can edit this dataset"""
        return user == self.owner or user in self.collaborators.all() or user.is_staff


class DatasetFile(models.Model):
    """Individual files within a dataset"""

    FILE_TYPES = [
        ("data", "Data File"),
        ("code", "Code File"),
        ("documentation", "Documentation"),
        ("metadata", "Metadata"),
        ("readme", "README"),
        ("license", "License"),
        ("figure", "Figure/Image"),
        ("supplementary", "Supplementary"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="files")

    # File information
    filename = models.CharField(max_length=500)
    file_path = models.CharField(max_length=1000, blank=True)  # Path within dataset
    file_type = models.CharField(max_length=30, choices=FILE_TYPES)
    file_format = models.CharField(max_length=50, blank=True)  # File extension

    # File metadata
    size_bytes = models.BigIntegerField()
    checksum_md5 = models.CharField(max_length=32, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    mime_type = models.CharField(max_length=200, blank=True)

    # Repository information
    repository_file_id = models.CharField(max_length=200, blank=True)
    download_url = models.URLField(blank=True)
    preview_url = models.URLField(blank=True)

    # File content metadata
    description = models.TextField(blank=True)
    encoding = models.CharField(max_length=50, blank=True)

    # Local copy (optional)
    local_file = models.FileField(upload_to="dataset_files/", blank=True, null=True)

    # Usage tracking
    download_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["file_path", "filename"]
        unique_together = ["dataset", "file_path", "filename"]
        indexes = [
            models.Index(fields=["dataset", "file_type"]),
            models.Index(fields=["file_format"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.get_file_type_display()})"

    def get_size_display(self):
        """Return human-readable file size"""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.1f} GB"


class DatasetVersion(models.Model):
    """Track versions of datasets for proper versioning"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="versions"
    )

    # Version information
    version_number = models.CharField(max_length=50)
    version_description = models.TextField(blank=True)
    is_current = models.BooleanField(default=False)

    # Repository information
    repository_version_id = models.CharField(max_length=200, blank=True)
    repository_version_url = models.URLField(blank=True)
    version_doi = models.CharField(max_length=100, blank=True)

    # Changes from previous version
    changes_summary = models.TextField(blank=True)
    files_added = models.IntegerField(default=0)
    files_modified = models.IntegerField(default=0)
    files_deleted = models.IntegerField(default=0)

    # Metadata snapshot
    metadata_snapshot = models.JSONField(default=dict)
    file_listing = models.JSONField(default=list)

    # Version relationships
    parent_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_versions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["dataset", "version_number"]
        indexes = [
            models.Index(fields=["dataset", "is_current"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.dataset.title} v{self.version_number}"
