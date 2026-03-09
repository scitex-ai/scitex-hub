"""
User Profile Models

UserProfile - Extended user profile for researchers
JAPANESE_ACADEMIC_DOMAINS - List of recognized Japanese academic domains
is_japanese_academic_email - Helper function to check academic status
"""

from django.contrib.auth.models import User
from django.db import models

# Japanese Academic domains to recognize
JAPANESE_ACADEMIC_DOMAINS = [
    # Japanese Academic (.ac.jp) - All academic institutions
    ".ac.jp",
    ".u-tokyo.ac.jp",
    ".kyoto-u.ac.jp",
    ".osaka-u.ac.jp",
    ".tohoku.ac.jp",
    ".nagoya-u.ac.jp",
    ".kyushu-u.ac.jp",
    ".hokudai.ac.jp",
    ".tsukuba.ac.jp",
    ".hiroshima-u.ac.jp",
    ".kobe-u.ac.jp",
    ".waseda.jp",
    ".keio.ac.jp",
    # Government Research Institutions (.go.jp)
    ".go.jp",  # Broader government research support
    ".riken.jp",
    ".aist.go.jp",
    ".nict.go.jp",
    ".jaxa.jp",
    ".jst.go.jp",
    ".nims.go.jp",
    ".nies.go.jp",
]


def is_japanese_academic_email(email):
    """Check if email belongs to Japanese academic institution"""
    if not email:
        return False
    try:
        domain = email.lower().split("@")[1]
        # Check if domain matches exactly or ends with the academic domain
        for academic_domain in JAPANESE_ACADEMIC_DOMAINS:
            # Remove leading dot for exact matching
            clean_domain = academic_domain.lstrip(".")
            if domain == clean_domain or domain.endswith(academic_domain):
                return True
        return False
    except (IndexError, AttributeError):
        return False


class UserProfile(models.Model):
    """Extended user profile for researchers"""

    VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("restricted", "Restricted"),
        ("private", "Private"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, help_text="Profile picture"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Brief description of your research background",
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Your current location (e.g., 'Tokyo, Japan')",
    )
    timezone = models.CharField(
        max_length=100,
        blank=True,
        default="UTC",
        help_text="Your timezone (e.g., 'Asia/Tokyo')",
    )
    institution = models.CharField(
        max_length=200, blank=True, help_text="Your current institution"
    )
    research_interests = models.TextField(
        max_length=500, blank=True, help_text="Your research areas and interests"
    )
    website = models.URLField(
        blank=True, help_text="Your personal or professional website"
    )

    # Academic information
    orcid = models.CharField(
        max_length=19,
        blank=True,
        help_text="Your ORCID identifier (e.g., 0000-0000-0000-0000)",
    )
    academic_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Your academic title (e.g., PhD, Professor)",
    )
    department = models.CharField(
        max_length=200, blank=True, help_text="Your department or faculty"
    )

    # Professional links
    google_scholar = models.URLField(
        blank=True, help_text="Your Google Scholar profile"
    )
    linkedin = models.URLField(blank=True, help_text="Your LinkedIn profile")
    researchgate = models.URLField(blank=True, help_text="Your ResearchGate profile")
    twitter = models.CharField(
        max_length=50, blank=True, help_text="Your Twitter handle (without @)"
    )

    # Git hosting profiles (for public bio display)
    github_profile = models.CharField(
        max_length=100, blank=True, help_text="Your GitHub username"
    )
    gitlab_profile = models.CharField(
        max_length=100, blank=True, help_text="Your GitLab username"
    )
    bitbucket_profile = models.CharField(
        max_length=100, blank=True, help_text="Your Bitbucket username"
    )

    # Privacy settings
    profile_visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="public",
        help_text="Who can view your profile",
    )
    is_public = models.BooleanField(default=True, help_text="Make profile public")
    show_email = models.BooleanField(
        default=False, help_text="Show email in public profile"
    )
    allow_collaboration = models.BooleanField(
        default=True, help_text="Allow collaboration requests"
    )
    allow_messages = models.BooleanField(
        default=True, help_text="Allow messages from other users"
    )

    # Academic institution recognition
    is_academic_ja = models.BooleanField(
        default=False,
        help_text="Automatically detected: User belongs to Japanese academic institution",
    )

    # Last active repository tracking
    last_active_repository = models.ForeignKey(
        "project_app.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="last_active_for_users",
        help_text="Last repository the user was working on",
    )

    # SSH Key Management
    ssh_public_key = models.TextField(
        blank=True, help_text="User's SSH public key for Git operations"
    )
    ssh_key_fingerprint = models.CharField(
        max_length=100, blank=True, help_text="SSH key fingerprint (SHA256)"
    )
    ssh_key_created_at = models.DateTimeField(
        null=True, blank=True, help_text="When SSH key was generated"
    )
    ssh_key_last_used_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time SSH key was used"
    )

    # Git Platform Integration Tokens
    github_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="GitHub Personal Access Token for importing private repos",
    )
    gitlab_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="GitLab Personal Access Token for importing private repos",
    )
    bitbucket_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Bitbucket App Password for importing private repos",
    )

    # Account deletion
    deletion_scheduled_at = models.DateTimeField(
        null=True, blank=True, help_text="When account deletion was scheduled"
    )

    # OS-level isolation: each Django user maps to a real Linux UID/GID.
    # UID = 100000 + user.pk (deterministic, LDAP-ready).
    # Set automatically via signals.py on user creation.
    unix_uid = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="Linux UID for OS-level process isolation (100000 + user.pk)",
    )
    unix_gid = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Linux GID for OS-level process isolation (same as unix_uid)",
    )

    # Apptainer container override — empty means use the shared default SIF
    apptainer_container_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Absolute path to a custom Apptainer .sif or sandbox directory. "
            "Leave blank to use the shared default container."
        ),
    )

    # MCP tool group preferences for Claude Code in Apptainer
    mcp_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="MCP tool group toggles: {GROUP_NAME: bool}",
    )

    # Auto-response preferences for Claude Code CLI prompt automation
    auto_response_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Auto-response config: {y_n, y_y_n, waiting, suggestion}",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        db_table = (
            "core_app_userprofile"  # Keep the same table name for smooth migration
        )

    def __str__(self):
        return f"Profile for {self.user.get_full_name() or self.user.username}"

    def get_display_name(self):
        """Get the best display name for the user"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username

    def get_ssh_manager(self):
        """Get SSH key manager for this user"""
        from apps.api.v1.auth.ssh_key_manager import SSHKeyManager

        return SSHKeyManager(self.user)

    def get_full_title(self):
        """Get full academic title and name"""
        name = self.get_display_name()
        if self.academic_title:
            return f"{self.academic_title} {name}"
        return name

    def is_complete(self):
        """Check if profile has essential information"""
        return bool(self.bio and self.institution and self.research_interests)

    @property
    def total_documents(self):
        """Get total number of documents created by the user"""
        return self.user.documents.count()

    @property
    def total_projects(self):
        """Get total number of projects owned by the user"""
        return self.user.owned_projects.count()

    def get_user_projects(self):
        """Get all projects owned by the user, ordered by last activity"""
        from apps.project_app.models import Project

        return Project.objects.filter(owner=self.user).order_by("-updated_at")

    def get_active_project(self):
        """Get active project, auto-defaulting to first owned project.

        If last_active_repository is unset, picks the first project and
        persists the choice so subsequent requests are fast.
        Only returns projects owned by the user.
        """
        try:
            if self.last_active_repository_id:
                lar = self.last_active_repository
                # Only return if user owns this project
                if lar.owner_id == self.user_id:
                    return lar
                # Clear stale cross-user reference
                self.last_active_repository = None
                self.save(update_fields=["last_active_repository"])
            first = self.get_user_projects().first()
            if first:
                self.last_active_repository = first
                self.save(update_fields=["last_active_repository"])
            return first
        except Exception:
            # DB connection may be in a failed transaction state (e.g. after
            # PgBouncer returns a dirty connection on startup).  Return None
            # so the template renders gracefully instead of raising 500.
            return None

    @property
    def total_collaborations(self):
        """Get total number of collaborations"""
        # Import here to avoid circular dependency
        from apps.project_app.models import ProjectPermission

        return ProjectPermission.objects.filter(user=self.user).count()

    def get_social_links(self):
        """Get available social/professional links"""
        links = []
        if self.website:
            links.append(("Website", self.website))
        if self.google_scholar:
            links.append(("Google Scholar", self.google_scholar))
        if self.linkedin:
            links.append(("LinkedIn", self.linkedin))
        if self.researchgate:
            links.append(("ResearchGate", self.researchgate))
        if self.twitter:
            links.append(("Twitter", f"https://twitter.com/{self.twitter}"))
        return links

    def update_academic_status(self):
        """Update is_academic_ja flag based on user's email"""
        self.is_academic_ja = is_japanese_academic_email(self.user.email)
        return self.is_academic_ja

    def get_academic_status_display(self):
        """Get display text for academic status"""
        if self.is_academic_ja:
            return "Japanese Academic Institution"
        return "General User"

    def save(self, *args, **kwargs):
        """Override save to automatically update academic status"""
        # Update academic status before saving
        self.update_academic_status()
        super().save(*args, **kwargs)
