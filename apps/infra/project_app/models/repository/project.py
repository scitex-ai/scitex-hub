"""
Repository Project Models
Contains: Project, ProjectMembership
"""

from django.contrib.auth.models import User
from django.db import models

# Import Organization models from dedicated app
from apps.infra.organizations_app.models import Organization, ResearchGroup

from .project_gitea_methods import ProjectGiteaMethodsMixin
from .project_managers import ProjectManager

# Import mixins and managers
from .project_methods import ProjectMethodsMixin
from .project_scitex_methods import ProjectSciTeXMethodsMixin


class ProjectMembership(models.Model):
    """Enhanced membership model for project collaboration"""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Administrator"),
        ("collaborator", "Collaborator"),
        ("viewer", "Viewer"),
    ]

    PERMISSION_CHOICES = [
        ("read", "Read Only"),
        ("write", "Read/Write"),
        ("admin", "Full Admin"),
    ]

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="collaborator")
    permission_level = models.CharField(
        max_length=20, choices=PERMISSION_CHOICES, default="read"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_invitations_sent",
    )

    class Meta:
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.role})"


class Project(
    ProjectMethodsMixin,
    ProjectGiteaMethodsMixin,
    ProjectSciTeXMethodsMixin,
    models.Model,
):
    """Model for research projects with enhanced collaboration"""

    VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
    ]

    PROJECT_TYPES = [
        ("local", "Local Repository"),  # Git-enabled, Gitea
        ("remote", "Remote Filesystem"),  # SSHFS mount, no Git
        ("trip", "Remote TRIP"),  # On-demand SSH, no local copy
    ]

    SOURCE_CHOICES = [
        ("scitex", "Created in SciTeX"),
        ("github", "Imported from GitHub"),
        ("gitlab", "Imported from GitLab"),
        ("bitbucket", "Imported from Bitbucket"),
        ("git", "Cloned from Git URL"),
    ]

    # Basic Information
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, default="project")
    description = models.TextField()
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_app_owned_projects"
    )

    # Project Type (local vs remote)
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPES,
        default="local",
        help_text="Local (Git-enabled) or Remote (SSH mount, no Git)",
    )

    # Privacy settings
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="public",
        help_text="Repository visibility: public (anyone can see) or private (only collaborators)",
    )

    # Organization and Research Group
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    org_owner = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_projects",
        help_text="Organization owner (if org-owned project)",
    )
    research_group = models.ForeignKey(
        ResearchGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Associated research group/lab",
    )

    # Enhanced collaboration through ProjectMembership
    collaborators = models.ManyToManyField(
        User,
        through="ProjectMembership",
        through_fields=("project", "user"),
        related_name="project_app_collaborative_projects",
    )

    # Project Progress and Timestamps
    progress = models.IntegerField(
        default=0, help_text="Project progress percentage (0-100)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(null=True, blank=True)

    # Research data - Core SciTeX workflow fields
    source_code_url = models.URLField(
        blank=True, help_text="GitHub/GitLab repository URL"
    )
    data_location = models.CharField(
        max_length=500, blank=True, help_text="Relative path to project directory"
    )

    # Enhanced GitHub Integration fields
    github_token = models.CharField(
        max_length=255, blank=True, help_text="GitHub OAuth token"
    )
    github_repo_id = models.IntegerField(
        null=True, blank=True, help_text="GitHub repository ID"
    )
    github_repo_name = models.CharField(
        max_length=200, blank=True, help_text="GitHub repository name"
    )
    github_owner = models.CharField(
        max_length=100, blank=True, help_text="GitHub repository owner"
    )
    current_branch = models.CharField(
        max_length=100, default="main", help_text="Current git branch"
    )
    last_sync_at = models.DateTimeField(
        null=True, blank=True, help_text="Last GitHub sync timestamp"
    )
    github_integration_enabled = models.BooleanField(
        default=False, help_text="GitHub integration status"
    )

    # Gitea Integration fields
    gitea_repo_id = models.IntegerField(
        null=True, blank=True, help_text="Gitea repository ID"
    )
    gitea_repo_name = models.CharField(
        max_length=200, blank=True, help_text="Gitea repository name"
    )
    gitea_repo_url = models.URLField(blank=True, help_text="Gitea repository web URL")
    gitea_clone_url = models.URLField(blank=True, help_text="Gitea HTTPS clone URL")
    gitea_ssh_url = models.CharField(
        max_length=500, blank=True, help_text="Gitea SSH clone URL"
    )
    git_url = models.URLField(blank=True, help_text="Git clone URL (SSH or HTTPS)")
    git_clone_path = models.CharField(
        max_length=500, blank=True, help_text="Local git clone path"
    )
    gitea_enabled = models.BooleanField(
        default=False, help_text="Gitea integration enabled"
    )

    # Source tracking (where did this project come from?)
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="scitex",
        help_text="Project source",
    )
    source_url = models.URLField(
        blank=True, help_text="Original source URL (if imported)"
    )

    # Directory management fields
    directory_created = models.BooleanField(
        default=False, help_text="Whether project directory has been created"
    )
    storage_used = models.BigIntegerField(
        default=0, help_text="Storage used by project in bytes"
    )
    last_activity = models.DateTimeField(
        auto_now=True, help_text="Last activity in project directory"
    )

    # SciTeX Integration (scitex.project package)
    scitex_project_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique identifier linking to scitex/.metadata/ (from scitex.project package)",
    )
    local_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to local project directory (where scitex/.metadata/ lives)",
    )

    # SciTeX Engine Integration Status
    search_completed = models.BooleanField(
        default=False, help_text="Literature search completed"
    )
    knowledge_gap_identified = models.TextField(
        blank=True, help_text="Identified knowledge gaps"
    )
    analysis_completed = models.BooleanField(
        default=False, help_text="Code analysis completed"
    )
    figures_generated = models.BooleanField(
        default=False, help_text="Visualizations generated"
    )
    manuscript_generated = models.BooleanField(
        default=False, help_text="Manuscript generated"
    )

    # App Marketplace fields (nullable — only required at submission)
    is_app = models.BooleanField(
        default=False,
        help_text="Whether this project is a SciTeX app plugin",
    )
    app_category = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        default="",
        help_text="App category for marketplace listing",
    )
    app_license = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="AGPL-3.0",
        help_text="SPDX license identifier for app distribution",
    )
    app_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        help_text="Marketplace submission status",
    )
    app_submitted_at = models.DateTimeField(blank=True, null=True)
    app_reviewed_at = models.DateTimeField(blank=True, null=True)
    app_reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_apps",
    )

    # Home project flag — undeletable, always private, one per user
    is_home = models.BooleanField(
        default=False,
        help_text="Dotfiles project: persistent, always private, cannot be deleted",
    )

    # Language detection
    primary_language = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Auto-detected primary programming language",
    )

    # Topic tags (like GitHub "About" topics)
    topics = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Comma-separated topic tags (e.g., python,machine-learning,statistics)",
    )

    # Custom Manager
    objects = ProjectManager()

    @property
    def is_org_owned(self):
        return self.org_owner_id is not None

    @property
    def effective_owner_slug(self):
        """GitHub-style: org slug or username."""
        if self.org_owner:
            return self.org_owner.slug
        return self.owner.username

    @property
    def effective_owner_name(self):
        if self.org_owner:
            return self.org_owner.name
        return self.owner.get_full_name() or self.owner.username

    class Meta:
        ordering = ["-updated_at"]
        unique_together = [
            ("name", "owner"),  # Ensure unique project names per user
            ("owner", "slug"),  # Ensure unique slugs per user
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "gitea_repo_name"],
                condition=models.Q(gitea_enabled=True),
                name="unique_gitea_repo_per_user",
            ),
            models.UniqueConstraint(
                fields=["gitea_repo_id"],
                condition=models.Q(gitea_repo_id__isnull=False),
                name="unique_gitea_repo_id",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.name, owner=self.owner)
        # Home project is always private
        if self.is_home:
            self.visibility = "private"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_home:
            raise ValueError("Dotfiles project cannot be deleted")
        return super().delete(*args, **kwargs)
