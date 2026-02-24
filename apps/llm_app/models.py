from django.db import models
from django.utils import timezone

from apps.integrations_app.models import IntegrationConnection


class LLMConnection(models.Model):
    """Extended configuration for LLM service connections"""

    connection = models.OneToOneField(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name="llm_connection",
        help_text="Base integration connection",
    )

    # Model configuration
    default_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Default model identifier (e.g., claude-sonnet-4-5-20250929)",
    )

    # Usage tracking
    total_tokens_used = models.BigIntegerField(
        default=0, help_text="Total tokens consumed across all requests"
    )
    total_requests = models.IntegerField(
        default=0, help_text="Total number of API requests made"
    )
    last_request_at = models.DateTimeField(null=True, blank=True)

    # Rate limiting (None = unlimited)
    daily_request_limit = models.IntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Maximum requests per day (empty = unlimited)",
    )
    daily_token_limit = models.IntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Maximum tokens per day (empty = unlimited)",
    )
    daily_cost_limit_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text="Maximum cost in USD per day (empty = unlimited)",
    )

    # Cost tracking
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Estimated total cost in USD",
    )

    # Feature flags
    enabled_features = models.JSONField(
        default=list,
        blank=True,
        help_text="List of enabled features (improve_clarity, summarize, etc.)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LLM Connection"
        verbose_name_plural = "LLM Connections"

    def __str__(self):
        return (
            f"{self.connection.user.username} - {self.connection.get_service_display()}"
        )

    def get_daily_usage(self):
        """Get usage statistics for the current day"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_logs = self.connection.llm_usage_logs.filter(created_at__gte=today_start)

        return {
            "requests": daily_logs.count(),
            "tokens": daily_logs.aggregate(models.Sum("total_tokens"))[
                "total_tokens__sum"
            ]
            or 0,
            "cost_usd": daily_logs.aggregate(models.Sum("estimated_cost_usd"))[
                "estimated_cost_usd__sum"
            ]
            or 0,
        }

    def check_rate_limits(self):
        """Check if rate limits would be exceeded by one more request"""
        daily_usage = self.get_daily_usage()

        if self.daily_request_limit is not None:
            if daily_usage["requests"] >= self.daily_request_limit:
                return False, "Daily request limit reached"

        if self.daily_token_limit is not None:
            if daily_usage["tokens"] >= self.daily_token_limit:
                return False, "Daily token limit reached"

        if self.daily_cost_limit_usd is not None:
            if daily_usage["cost_usd"] >= float(self.daily_cost_limit_usd):
                return False, "Daily cost limit reached"

        return True, None


class LLMUsageLog(models.Model):
    """Log individual LLM API requests for tracking and analysis"""

    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name="llm_usage_logs",
        help_text="Which LLM connection was used",
    )

    # Request context
    app_name = models.CharField(
        max_length=50, help_text="Which SciTeX app used the LLM (writer, scholar, etc.)"
    )
    feature = models.CharField(
        max_length=100, help_text="Feature name (improve_clarity, summarize, etc.)"
    )

    # Model details
    model_used = models.CharField(
        max_length=100, help_text="Specific model used for this request"
    )

    # Token usage
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # Performance
    response_time_ms = models.IntegerField(
        default=0, help_text="Response time in milliseconds"
    )

    # Cost
    estimated_cost_usd = models.DecimalField(
        max_digits=8, decimal_places=6, default=0, help_text="Estimated cost in USD"
    )

    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "LLM Usage Log"
        verbose_name_plural = "LLM Usage Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["connection", "-created_at"]),
            models.Index(fields=["app_name", "feature"]),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.app_name}/{self.feature} - {self.model_used} ({status})"
