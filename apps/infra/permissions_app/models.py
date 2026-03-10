"""
Permission models for SciTeX.
GitLab-inspired role-based access control.
"""

from django.db import models
from django.contrib.auth.models import User


class Role(models.TextChoices):
    """Project member roles (GitLab-style)."""

    OWNER = "owner", "Owner"
    MAINTAINER = "maintainer", "Maintainer"
    DEVELOPER = "developer", "Developer"
    REPORTER = "reporter", "Reporter"
    GUEST = "guest", "Guest"


class ProjectMember(models.Model):
    """User's role in a project."""

    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="permission_members",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="permission_project_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEVELOPER)

    # Module permissions (None = use role default)
    can_edit_scholar = models.BooleanField(null=True, blank=True)
    can_edit_code = models.BooleanField(null=True, blank=True)
    can_edit_viz = models.BooleanField(null=True, blank=True)
    can_edit_writer = models.BooleanField(null=True, blank=True)

    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="invited_members"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["project", "user"]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class GuestCollaborator(models.Model):
    """Email-based guest access (no account required)."""

    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        related_name="guest_collaborators",
        null=True,
        blank=True,
    )
    manuscript = models.ForeignKey(
        "writer_app.Manuscript",
        on_delete=models.CASCADE,
        related_name="guest_collaborators",
        null=True,
        blank=True,
    )

    email = models.EmailField()
    guest_name = models.CharField(max_length=200, blank=True)
    access_token = models.CharField(max_length=64, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)

    can_comment = models.BooleanField(default=True)
    can_download = models.BooleanField(default=True)

    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    invitation_sent_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    is_active = models.BooleanField(default=True)
    first_accessed_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-invitation_sent_at"]

    def is_valid(self):
        from django.utils import timezone

        return self.is_active and timezone.now() < self.expires_at
