"""
Collaboration Models
Contains: ProjectWatch, ProjectStar, ProjectFork, ProjectInvitation
"""

from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone


class ProjectWatch(models.Model):
    """
    Model to track users watching a project for notifications
    Similar to GitHub's watch feature
    """

    NOTIFICATION_CHOICES = [
        ("all", "All Activity"),
        ("participating", "Participating and @mentions"),
        ("ignoring", "Ignore"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_watches"
    )
    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, related_name="project_watchers"
    )
    notification_settings = models.CharField(
        max_length=20,
        choices=NOTIFICATION_CHOICES,
        default="all",
        help_text="Notification preference for this project",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")
        verbose_name = "Project Watch"
        verbose_name_plural = "Project Watches"
        indexes = [
            models.Index(fields=["user", "project"]),
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} watches {self.project.name}"


class ProjectStar(models.Model):
    """
    Model to track users starring a project
    Similar to GitHub's star feature - indicates interest/bookmarking
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_stars"
    )
    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, related_name="project_stars_set"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")
        verbose_name = "Project Star"
        verbose_name_plural = "Project Stars"
        indexes = [
            models.Index(fields=["user", "project"]),
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} starred {self.project.name}"


class ProjectFork(models.Model):
    """
    Model to track project forks
    Similar to GitHub's fork feature - creates a copy of a project
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_forks",
        help_text="User who created the fork",
    )
    original_project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="project_forks_set",
        help_text="The original project that was forked",
    )
    forked_project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="forked_from",
        help_text="The new forked project",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: Track if fork is synced with original
    last_sync_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time fork was synced with original"
    )

    class Meta:
        unique_together = ("user", "original_project", "forked_project")
        verbose_name = "Project Fork"
        verbose_name_plural = "Project Forks"
        indexes = [
            models.Index(fields=["user", "original_project"]),
            models.Index(fields=["original_project", "created_at"]),
            models.Index(fields=["forked_project"]),
        ]

    def __str__(self):
        return f"{self.user.username} forked {self.original_project.name} to {self.forked_project.name}"


class ProjectInvitation(models.Model):
    """
    Pending invitation to collaborate on a project.
    User must accept invitation to become a collaborator.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
    ]

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, related_name="invitations"
    )
    invited_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_invitations"
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ("owner", "Owner"),
            ("admin", "Administrator"),
            ("collaborator", "Collaborator"),
            ("viewer", "Viewer"),
        ],
        default="collaborator",
    )
    permission_level = models.CharField(
        max_length=20,
        choices=[
            ("read", "Read Only"),
            ("write", "Read/Write"),
            ("admin", "Full Admin"),
        ],
        default="write",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("project", "invited_user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invited_user.username} → {self.project.name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.token:
            import secrets

            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == "pending"

    def accept(self):
        """Accept invitation and create membership."""
        if self.status != "pending":
            return False

        from .core import ProjectMembership

        ProjectMembership.objects.create(
            project=self.project,
            user=self.invited_user,
            role=self.role,
            permission_level=self.permission_level,
            invited_by=self.invited_by,
        )

        self.status = "accepted"
        self.responded_at = timezone.now()
        self.save()
        return True

    def decline(self):
        """Decline invitation."""
        if self.status != "pending":
            return False

        self.status = "declined"
        self.responded_at = timezone.now()
        self.save()
        return True
