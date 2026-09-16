"""Core project permission models."""

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
