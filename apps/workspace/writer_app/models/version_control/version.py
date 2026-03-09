"""Version control models for writer_app."""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ManuscriptVersion(models.Model):
    """Track manuscript versions with comprehensive change history and branching."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="versions"
    )

    # Version identification
    version_number = models.CharField(max_length=20)  # e.g., "1.0", "1.1", "2.0-beta"
    version_tag = models.CharField(
        max_length=100, blank=True
    )  # e.g., "Initial Draft", "Reviewer Comments Addressed"
    branch_name = models.CharField(max_length=50, default="main")  # Git-style branching

    # Version metadata
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_versions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    commit_message = models.TextField(blank=True)

    # Content snapshot
    manuscript_data = models.JSONField()  # Complete manuscript state at this version
    section_contents = models.JSONField()  # Section-by-section content

    # Version relationships
    parent_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_versions",
    )
    is_major_version = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    # Statistics
    total_changes = models.IntegerField(default=0)
    word_count_delta = models.IntegerField(default=0)
    lines_added = models.IntegerField(default=0)
    lines_removed = models.IntegerField(default=0)

    # File attachments
    version_file = models.FileField(
        upload_to="manuscript_versions/", blank=True, null=True
    )
    diff_file = models.FileField(upload_to="manuscript_diffs/", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["manuscript", "version_number", "branch_name"]

    def __str__(self):
        return f"{self.manuscript.title} - v{self.version_number} ({self.branch_name})"

    def get_version_summary(self):
        """Get a summary of changes in this version."""
        return {
            "version": self.version_number,
            "branch": self.branch_name,
            "tag": self.version_tag,
            "author": self.created_by.username,
            "date": self.created_at,
            "message": self.commit_message,
            "changes": self.total_changes,
            "word_delta": self.word_count_delta,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
        }


class ManuscriptBranch(models.Model):
    """Manage manuscript branches for parallel development."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="branches"
    )

    # Branch identification
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    # Branch metadata
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_branches"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # Branch relationships
    parent_branch = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_branches",
    )
    base_version = models.ForeignKey(
        "ManuscriptVersion",
        on_delete=models.SET_NULL,
        null=True,
        related_name="branched_from",
    )

    # Branch status
    is_active = models.BooleanField(default=True)
    is_merged = models.BooleanField(default=False)
    merged_at = models.DateTimeField(null=True, blank=True)
    merged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merged_branches",
    )

    # Statistics
    total_commits = models.IntegerField(default=0)
    contributors = models.ManyToManyField(
        User, related_name="contributed_branches", blank=True
    )

    class Meta:
        ordering = ["-last_updated"]
        unique_together = ["manuscript", "name"]

    def __str__(self):
        return f"{self.manuscript.title} - {self.name} branch"

    def get_latest_version(self):
        """Get the latest version in this branch."""
        return self.manuscript.versions.filter(branch_name=self.name).first()

    def get_commits_ahead_behind(self, target_branch="main"):
        """Calculate commits ahead/behind target branch."""
        # Implementation for branch comparison
        target_versions = self.manuscript.versions.filter(
            branch_name=target_branch
        ).count()
        current_versions = self.manuscript.versions.filter(
            branch_name=self.name
        ).count()
        return {
            "ahead": max(0, current_versions - target_versions),
            "behind": max(0, target_versions - current_versions),
        }


class DiffResult(models.Model):
    """Store computed diffs between manuscript versions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="diffs"
    )

    # Diff identification
    from_version = models.ForeignKey(
        "ManuscriptVersion", on_delete=models.CASCADE, related_name="diffs_from"
    )
    to_version = models.ForeignKey(
        "ManuscriptVersion", on_delete=models.CASCADE, related_name="diffs_to"
    )

    # Diff data
    diff_type = models.CharField(
        max_length=20,
        choices=[
            ("unified", "Unified Diff"),
            ("side_by_side", "Side by Side"),
            ("word_level", "Word Level"),
            ("semantic", "Semantic Diff"),
        ],
        default="unified",
    )

    diff_data = models.JSONField()  # Structured diff information
    diff_html = models.TextField(blank=True)  # Pre-rendered HTML diff
    diff_stats = models.JSONField(default=dict)  # Statistics about the diff

    # Caching
    computed_at = models.DateTimeField(auto_now_add=True)
    is_cached = models.BooleanField(default=True)
    cache_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-computed_at"]
        unique_together = ["from_version", "to_version", "diff_type"]

    def __str__(self):
        return f"Diff: {self.from_version.version_number} → {self.to_version.version_number}"

    def is_valid_cache(self):
        """Check if cached diff is still valid."""
        if not self.is_cached:
            return False
        if self.cache_expires and timezone.now() > self.cache_expires:
            return False
        return True


class MergeRequest(models.Model):
    """Manage merge requests between manuscript branches."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "Manuscript", on_delete=models.CASCADE, related_name="merge_requests"
    )

    # Merge identification
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Branch information
    source_branch = models.ForeignKey(
        "ManuscriptBranch", on_delete=models.CASCADE, related_name="merge_requests_from"
    )
    target_branch = models.ForeignKey(
        "ManuscriptBranch", on_delete=models.CASCADE, related_name="merge_requests_to"
    )
    source_version = models.ForeignKey(
        "ManuscriptVersion",
        on_delete=models.CASCADE,
        related_name="merge_requests_from_version",
    )
    target_version = models.ForeignKey(
        "ManuscriptVersion",
        on_delete=models.CASCADE,
        related_name="merge_requests_to_version",
    )

    # Request metadata
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_merge_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Review process
    status = models.CharField(
        max_length=20,
        choices=[
            ("open", "Open"),
            ("review", "In Review"),
            ("approved", "Approved"),
            ("merged", "Merged"),
            ("closed", "Closed"),
            ("draft", "Draft"),
        ],
        default="open",
    )

    reviewers = models.ManyToManyField(
        User, related_name="merge_requests_to_review", blank=True
    )
    approved_by = models.ManyToManyField(
        User, related_name="approved_merge_requests", blank=True
    )

    # Merge information
    merged_at = models.DateTimeField(null=True, blank=True)
    merged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merged_requests",
    )
    merge_commit = models.ForeignKey(
        "ManuscriptVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merge_commit_for",
    )

    # Conflict resolution
    has_conflicts = models.BooleanField(default=False)
    conflict_data = models.JSONField(default=dict)
    auto_mergeable = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"MR: {self.source_branch.name} → {self.target_branch.name}"

    def can_auto_merge(self):
        """Check if merge request can be automatically merged."""
        return (
            self.auto_mergeable and not self.has_conflicts and self.status == "approved"
        )
