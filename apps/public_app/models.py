from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

# Donation models moved to apps.donations_app.models
# Import here for backwards compatibility
from apps.donations_app.models import Donation, DonationTier  # noqa

# EmailVerification model moved to apps.auth_app.models
# Import here for backwards compatibility
from apps.auth_app.models import EmailVerification  # noqa

# EmailVerification, Donation and DonationTier model definitions moved to their respective apps
# Import statements at top of file provide backwards compatibility

# Models for SciTeX-Cloud services


class SubscriptionPlan(models.Model):
    """Model for subscription plans."""

    PLAN_TYPES = [
        ("free", "Free"),
        ("premium_a", "Premium A"),
        ("premium_b", "Premium B"),
        ("enterprise", "Enterprise"),
        ("custom", "Custom"),
    ]

    # Basic information
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Resource limits
    max_projects = models.IntegerField(default=1)
    storage_gb = models.IntegerField(default=5)
    cpu_cores = models.IntegerField(default=2)
    gpu_vram_gb = models.IntegerField(default=2)

    # Feature flags
    has_watermark = models.BooleanField(default=True)
    requires_citation = models.BooleanField(default=True)
    requires_archive = models.BooleanField(default=True)
    has_priority_support = models.BooleanField(default=False)
    has_custom_integrations = models.BooleanField(default=False)
    has_team_collaboration = models.BooleanField(default=False)

    # Display
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "price_monthly"]

    def __str__(self):
        return f"{self.name} - ${self.price_monthly}/month"


class Subscription(models.Model):
    """Model for user subscriptions."""

    SUBSCRIPTION_STATUS = [
        ("trial", "Trial"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ]

    # Relationships
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cloud_subscriptions"
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)

    # Status
    status = models.CharField(
        max_length=20, choices=SUBSCRIPTION_STATUS, default="trial"
    )

    # Billing
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)

    # Dates
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    canceled_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    def is_active(self):
        """Check if subscription is currently active."""
        return (
            self.status in ["trial", "active"]
            and timezone.now() < self.current_period_end
        )


class CloudResource(models.Model):
    """Model for tracking cloud resource usage."""

    RESOURCE_TYPES = [
        ("cpu", "CPU Time"),
        ("gpu", "GPU Time"),
        ("storage", "Storage"),
        ("bandwidth", "Bandwidth"),
        ("api_calls", "API Calls"),
    ]

    # Relationships
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cloud_resources"
    )
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)

    # Resource details
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    amount_used = models.DecimalField(max_digits=20, decimal_places=6)
    unit = models.CharField(max_length=20)  # e.g., 'hours', 'GB', 'requests'

    # Tracking
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "resource_type", "period_start"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.resource_type}: {self.amount_used} {self.unit}"


class APIKey(models.Model):
    """Model for API keys to access SciTeX services."""

    # Relationships
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cloud_api_keys"
    )

    # Key details
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    prefix = models.CharField(
        max_length=8, blank=True
    )  # Visible prefix for identification

    # Permissions
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    # Rate limiting
    rate_limit_per_hour = models.IntegerField(default=1000)

    # Status
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.prefix:
            self.prefix = str(self.key)[:8]
        super().save(*args, **kwargs)


class ServiceIntegration(models.Model):
    """Model for tracking integrations with external services."""

    INTEGRATION_TYPES = [
        ("orcid", "ORCID"),
        ("github", "GitHub"),
        ("gitlab", "GitLab"),
        ("zenodo", "Zenodo"),
        ("figshare", "Figshare"),
        ("mendeley", "Mendeley"),
        ("zotero", "Zotero"),
    ]

    # Relationships
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cloud_integrations"
    )

    # Integration details
    integration_type = models.CharField(max_length=20, choices=INTEGRATION_TYPES)
    external_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True)  # Encrypted in practice
    refresh_token = models.TextField(blank=True)  # Encrypted in practice

    # Status
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "integration_type"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.integration_type}"


class Contributor(models.Model):
    """Model for GitHub contributors."""

    ROLE_CHOICES = [
        ("creator", "Creator"),
        ("maintainer", "Maintainer"),
        ("core", "Core Team"),
        ("contributor", "Contributor"),
    ]

    # Basic info
    github_username = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    # Role and status
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="contributor")
    is_core_team = models.BooleanField(default=False)

    # Contribution stats
    contributions = models.IntegerField(default=0)
    contributions_description = models.TextField(blank=True)

    # Display order (lower number = higher priority)
    display_order = models.IntegerField(default=1000)

    # Timestamps
    first_contribution = models.DateTimeField(null=True, blank=True)
    last_contribution = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-contributions", "-last_contribution"]

    def __str__(self):
        return f"{self.github_username} ({self.role})"


class ServerMetrics(models.Model):
    """Model for storing server performance metrics over time for analysis."""

    # Timestamp (unique per collection interval)
    timestamp = models.DateTimeField(db_index=True)

    # CPU metrics
    cpu_percent = models.FloatField(help_text="CPU usage percentage (0-100)")
    cpu_cores = models.IntegerField(null=True, blank=True, help_text="Number of physical CPU cores")
    cpu_cores_logical = models.IntegerField(null=True, blank=True, help_text="Number of logical CPU cores")

    # Memory metrics
    memory_percent = models.FloatField(help_text="Memory usage percentage (0-100)")
    memory_used_gb = models.FloatField(help_text="Memory used in GB")
    memory_total_gb = models.FloatField(help_text="Total memory in GB")
    memory_available_gb = models.FloatField(help_text="Available memory in GB")

    # Disk metrics
    disk_percent = models.FloatField(help_text="Disk usage percentage (0-100)")
    disk_used_gb = models.FloatField(help_text="Disk space used in GB")
    disk_total_gb = models.FloatField(help_text="Total disk space in GB")
    disk_read_mb = models.FloatField(help_text="Total disk read in MB since boot")
    disk_write_mb = models.FloatField(help_text="Total disk write in MB since boot")

    # Network metrics
    net_sent_mb = models.FloatField(help_text="Total network sent in MB since boot")
    net_recv_mb = models.FloatField(help_text="Total network received in MB since boot")

    # Optional service status
    docker_services_running = models.IntegerField(null=True, blank=True, help_text="Number of running Docker services")
    ssh_gateway_status = models.BooleanField(default=False, help_text="SSH gateway service status")
    gitea_ssh_status = models.BooleanField(default=False, help_text="Gitea SSH service status")
    database_status = models.BooleanField(default=False, help_text="Database connection status")
    redis_status = models.BooleanField(default=False, help_text="Redis cache status")

    # Visitor pool metrics
    visitor_pool_allocated = models.IntegerField(null=True, blank=True, help_text="Number of allocated visitor slots")
    visitor_pool_total = models.IntegerField(null=True, blank=True, help_text="Total visitor pool size")

    # User activity metrics
    active_users_count = models.IntegerField(null=True, blank=True, help_text="Number of currently logged-in users")

    # GPU metrics
    gpu_percent = models.FloatField(null=True, blank=True, help_text="GPU usage percentage (0-100)")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
        ]
        verbose_name = "Server Metric"
        verbose_name_plural = "Server Metrics"

    def __str__(self):
        return f"Metrics at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
