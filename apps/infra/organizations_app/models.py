"""
Organizations App Models

This app manages organizations and research groups.
Extracted from workspace_app and project_app to resolve model duplication.

See: project_management/MODEL_DUPLICATION_DECISION.md
"""

from django.contrib.auth.models import User
from django.db import models


class Organization(models.Model):
    """
    Model for research organizations (universities, institutes, companies).

    Canonical source for Organization model - previously duplicated in
    workspace_app and project_app.

    Organizations can own projects just like users (GitHub-style).
    URL pattern: /<slug>/ (e.g., /scitex-ai/)
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="URL-friendly identifier (e.g., 'scitex-ai')",
    )
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    avatar = models.ImageField(
        upload_to="organization_avatars/",
        blank=True,
        null=True,
        help_text="Organization avatar/logo",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional: Members relationship through OrganizationMembership
    members = models.ManyToManyField(
        User, through="OrganizationMembership", related_name="organizations"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            from django.utils.text import slugify

            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Get URL for this organization's profile page"""
        return f"/{self.slug}/"

    def can_edit(self, user):
        """Check if user can edit this organization"""
        if not user.is_authenticated:
            return False
        membership = self.memberships.filter(user=user).first()
        return membership and membership.role == "admin"

    def can_create_project(self, user):
        """Check if user can create projects for this organization"""
        if not user.is_authenticated:
            return False
        membership = self.memberships.filter(user=user).first()
        return membership and membership.role in ["admin", "member"]

    @property
    def username(self):
        """Compatibility property for URL generation (same as slug)"""
        return self.slug

    @property
    def avatar_static_url(self):
        """Return static URL for known orgs without uploaded avatars."""
        STATIC_AVATARS = {
            "scitex-apps": "shared/images/scitex_logos/scitex-icon/scitex-icon-green.svg",
        }
        return STATIC_AVATARS.get(self.slug)


class OrganizationMembership(models.Model):
    """
    Model for organization membership with roles.

    Defines user membership in organizations with role-based access.
    """

    ROLES = [
        ("admin", "Administrator"),
        ("member", "Member"),
        ("viewer", "Viewer"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organization_memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=ROLES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization")
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"


class ResearchGroup(models.Model):
    """
    Model for research groups/labs within organizations.

    Research groups are sub-units within organizations (e.g., labs within universities).
    """

    name = models.CharField(max_length=200)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="research_groups"
    )
    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_research_groups",
        help_text="Principal Investigator or group leader",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Members relationship through ResearchGroupMembership
    members = models.ManyToManyField(
        User, through="ResearchGroupMembership", related_name="research_groups"
    )

    class Meta:
        ordering = ["organization__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class ResearchGroupMembership(models.Model):
    """
    Model for research group membership with academic roles.

    Defines user membership in research groups with role-based permissions
    and academic position tracking.
    """

    GROUP_ROLES = [
        ("pi", "Principal Investigator"),
        ("postdoc", "Postdoctoral Researcher"),
        ("phd", "PhD Student"),
        ("masters", "Masters Student"),
        ("undergrad", "Undergraduate Student"),
        ("researcher", "Research Staff"),
        ("visiting", "Visiting Researcher"),
        ("collaborator", "External Collaborator"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_memberships"
    )
    group = models.ForeignKey(
        ResearchGroup, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=GROUP_ROLES, default="researcher")

    # Permissions within group
    can_create_projects = models.BooleanField(
        default=True, help_text="Can create new projects for the group"
    )
    can_invite_collaborators = models.BooleanField(
        default=False, help_text="Can invite external collaborators"
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "group")
        ordering = ["joined_at"]

    def __str__(self):
        user_display = self.user.get_full_name() or self.user.username
        return f"{user_display} - {self.group.name} ({self.role})"
