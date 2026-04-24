"""
Core Project Models
Contains: ProjectPermission, VisitorAllocation
(Project and ProjectMembership moved to repository/project.py)
"""

from django.db import models


class ProjectPermission(models.Model):
    """Granular permissions for project resources"""

    RESOURCE_CHOICES = [
        ("files", "Files"),
        ("documents", "Documents"),
        ("code", "Code"),
        ("data", "Data"),
        ("settings", "Settings"),
    ]

    PERMISSION_CHOICES = [
        ("view", "View"),
        ("edit", "Edit"),
        ("delete", "Delete"),
        ("admin", "Admin"),
    ]

    membership = models.ForeignKey(
        "ProjectMembership",
        on_delete=models.CASCADE,
        related_name="project_permissions",
    )
    resource_type = models.CharField(max_length=20, choices=RESOURCE_CHOICES)
    permission_level = models.CharField(max_length=20, choices=PERMISSION_CHOICES)

    class Meta:
        unique_together = ("membership", "resource_type")

    def __str__(self):
        return f"{self.membership.user.username} - {self.resource_type}: {self.permission_level}"


class VisitorAllocation(models.Model):
    """
    Tracks visitor pool slot allocations.

    Prevents race conditions when allocating visitor accounts to sessions.
    Used by VisitorPool service for managing visitor-001 to visitor-004 (default pool size).
    """

    visitor_number = models.IntegerField(
        unique=True, help_text="Visitor slot number (1-4 default, configurable)"
    )
    session_key = models.CharField(
        max_length=255, blank=True, help_text="Django session key"
    )
    allocation_token = models.CharField(
        max_length=64, unique=True, help_text="Security token"
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Allocation expiry time")
    is_active = models.BooleanField(default=True, help_text="Active allocation")
    last_activity = models.DateTimeField(
        null=True, blank=True, help_text="Last activity timestamp for idle detection"
    )
    workspace_ready = models.BooleanField(
        default=False,
        help_text="Whether async workspace initialization (template clone) has completed",
    )

    class Meta:
        ordering = ["visitor_number"]
        indexes = [
            models.Index(fields=["is_active", "expires_at"]),
            models.Index(fields=["session_key"]),
            models.Index(fields=["allocation_token"]),
        ]

    def __str__(self):
        status = "active" if self.is_active else "expired"
        return f"visitor-{self.visitor_number:03d} ({status})"
