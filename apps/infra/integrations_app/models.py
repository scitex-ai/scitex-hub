import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def _get_fernet_key() -> bytes:
    """Derive a valid 32-byte Fernet key from Django's SECRET_KEY."""
    return base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )


class IntegrationConnection(models.Model):
    """Base model for external service integrations"""

    SERVICE_CHOICES = [
        ("orcid", "ORCID"),
        ("github", "GitHub"),
        ("gitlab", "GitLab"),
        ("zotero", "Zotero"),
        ("overleaf", "Overleaf"),
        ("slack", "Slack"),
        ("discord", "Discord"),
        ("anthropic", "Anthropic (Claude)"),
        ("openai", "OpenAI (GPT)"),
        ("gemini", "Google (Gemini)"),
        ("mistral", "Mistral AI"),
        ("xai", "xAI (Grok)"),
        ("deepseek", "DeepSeek"),
        ("mimo", "Xiaomi MiMo"),
        ("openrouter", "OpenRouter"),
        ("ollama", "Ollama (local)"),
        ("local_llm", "Local LLM (Ollama/LM Studio)"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("error", "Error"),
        ("expired", "Expired"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="integration_connections"
    )
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="inactive")

    # OAuth tokens (encrypted)
    access_token = models.TextField(
        blank=True, help_text="Encrypted OAuth access token"
    )
    refresh_token = models.TextField(
        blank=True, help_text="Encrypted OAuth refresh token"
    )
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # API keys (encrypted)
    api_key = models.TextField(blank=True, help_text="Encrypted API key")
    api_secret = models.TextField(blank=True, help_text="Encrypted API secret")

    # Service-specific data
    external_user_id = models.CharField(
        max_length=255, blank=True, help_text="User ID on external service"
    )
    external_username = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Service-specific metadata"
    )

    # Webhook configuration
    webhook_url = models.URLField(blank=True, help_text="Webhook URL for notifications")
    webhook_secret = models.TextField(blank=True, help_text="Encrypted webhook secret")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "service")
        verbose_name = "Integration Connection"
        verbose_name_plural = "Integration Connections"

    def __str__(self):
        return f"{self.user.username} - {self.get_service_display()}"

    def encrypt_value(self, value):
        """Encrypt sensitive data"""
        if not value:
            return ""
        f = Fernet(_get_fernet_key())
        return f.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value):
        """Decrypt sensitive data"""
        if not encrypted_value:
            return ""
        f = Fernet(_get_fernet_key())
        return f.decrypt(encrypted_value.encode()).decode()

    def set_access_token(self, token):
        """Set encrypted access token"""
        self.access_token = self.encrypt_value(token)

    def get_access_token(self):
        """Get decrypted access token"""
        return self.decrypt_value(self.access_token)

    def set_api_key(self, key):
        """Set encrypted API key"""
        self.api_key = self.encrypt_value(key)

    def get_api_key(self):
        """Get decrypted API key"""
        return self.decrypt_value(self.api_key)

    def is_token_expired(self):
        """Check if OAuth token has expired"""
        if not self.token_expires_at:
            return False
        return timezone.now() >= self.token_expires_at


class ORCIDProfile(models.Model):
    """ORCID profile data"""

    connection = models.OneToOneField(
        IntegrationConnection, on_delete=models.CASCADE, related_name="orcid_profile"
    )
    orcid_id = models.CharField(
        max_length=19, unique=True, help_text="ORCID iD (e.g., 0000-0002-1825-0097)"
    )

    # Profile data
    given_names = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    biography = models.TextField(blank=True)

    # Affiliations
    current_institution = models.CharField(max_length=255, blank=True)
    affiliations = models.JSONField(default=list, blank=True)

    # Research areas
    keywords = models.JSONField(default=list, blank=True)

    # URLs
    profile_url = models.URLField(blank=True)
    website_urls = models.JSONField(default=list, blank=True)

    # Sync metadata
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ORCID Profile"
        verbose_name_plural = "ORCID Profiles"

    def __str__(self):
        return f"{self.orcid_id} - {self.given_names} {self.family_name}"

    def get_full_name(self):
        """Get full name"""
        return f"{self.given_names} {self.family_name}".strip()


class SlackWebhook(models.Model):
    """Slack webhook configuration"""

    EVENT_CHOICES = [
        ("project_created", "Project Created"),
        ("project_updated", "Project Updated"),
        ("manuscript_updated", "Manuscript Updated"),
        ("analysis_completed", "Analysis Completed"),
        ("figures_generated", "Figures Generated"),
    ]

    connection = models.ForeignKey(
        IntegrationConnection, on_delete=models.CASCADE, related_name="slack_webhooks"
    )
    webhook_url = models.URLField(help_text="Slack webhook URL")
    channel = models.CharField(
        max_length=100, blank=True, help_text="Target channel (optional)"
    )
    username = models.CharField(
        max_length=100, default="SciTeX", help_text="Bot username"
    )
    icon_emoji = models.CharField(
        max_length=50, default=":microscope:", help_text="Bot icon emoji"
    )

    # Event subscriptions
    enabled_events = models.JSONField(
        default=list, help_text="List of event types to notify"
    )

    # Filters
    project_filter = models.ManyToManyField(
        "project_app.Project",
        blank=True,
        related_name="slack_webhooks",
        help_text="Only notify for these projects (empty = all)",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_notification_at = models.DateTimeField(null=True, blank=True)
    notification_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Slack Webhook"
        verbose_name_plural = "Slack Webhooks"

    def __str__(self):
        return f"Slack webhook for {self.connection.user.username}"


class Event(models.Model):
    """General-purpose event for async task results.

    Stores events from CLI, HPC, CI, or any external process.
    Used by the SciTeX event bus (scitex.events.emit → POST /api/events/).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(
        max_length=50, db_index=True, help_text="Event type (e.g., test_complete)"
    )
    project = models.CharField(max_length=100, db_index=True, help_text="Project name")
    status = models.CharField(max_length=20, help_text="success or failure")
    payload = models.JSONField(default=dict, help_text="Event-specific data")
    source = models.CharField(
        max_length=20, default="local", help_text="Origin: local, hpc, ci"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "type", "-created_at"]),
        ]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return f"{self.type} | {self.project} | {self.status} ({self.created_at})"


class IntegrationLog(models.Model):
    """Log integration activities"""

    ACTION_CHOICES = [
        ("connect", "Connected"),
        ("disconnect", "Disconnected"),
        ("sync", "Synced"),
        ("export", "Exported"),
        ("import", "Imported"),
        ("notify", "Notification Sent"),
        ("error", "Error"),
    ]

    connection = models.ForeignKey(
        IntegrationConnection, on_delete=models.CASCADE, related_name="logs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Integration Log"
        verbose_name_plural = "Integration Logs"

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.connection.service} - {self.action} ({status})"
