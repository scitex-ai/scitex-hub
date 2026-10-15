import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.infra.integrations_app.models import IntegrationConnection


def funded_dispatch_key() -> str:
    """Generate an opaque internal dispatch identity for migrated/admin rows."""

    return uuid.uuid4().hex


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


class ChatSession(models.Model):
    """A named chat conversation belonging to a user."""

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    title = models.CharField(max_length=200, default="New chat")
    share_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Public share token (URL key for read-only access)",
    )
    is_shared = models.BooleanField(
        default=False,
        help_text="Whether the session is publicly accessible via share_token",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class ChatMessage(models.Model):
    """A single message within a chat session."""

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=10)  # user | assistant | error
    text = models.TextField()
    tools_used = models.JSONField(default=list, blank=True)
    media = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.text[:60]}"


class FundedChatDailyQuota(models.Model):
    """Locked UTC-day counter for SciTeX-funded user messages."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="funded_chat_daily_quotas",
    )
    day = models.DateField()
    claimed_count = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "day"], name="uniq_funded_chat_quota_user_day"
            ),
            models.CheckConstraint(
                condition=models.Q(claimed_count__lte=10),
                name="funded_chat_claimed_lte_ten",
            ),
        ]


class FundedChatDailySpend(models.Model):
    """Locked provider/global cap row; provider and subsidy costs stay distinct."""

    GLOBAL_SCOPE = "__global__"

    day = models.DateField()
    scope = models.CharField(max_length=80)
    reserved_subsidy_usd = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("0")
    )
    provider_cost_usd = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("0")
    )
    subsidy_cost_usd = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("0")
    )
    requires_operator_repair = models.BooleanField(default=False)
    operator_repair_metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["day", "scope"], name="uniq_funded_chat_spend_day_scope"
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_subsidy_usd__gte=0),
                name="funded_spend_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(provider_cost_usd__gte=0),
                name="funded_spend_provider_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(subsidy_cost_usd__gte=0),
                name="funded_spend_subsidy_nonnegative",
            ),
        ]


class FundedChatRateBucket(models.Model):
    """Database-backed per-user abuse limit shared by every web worker."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="funded_chat_rate_buckets",
    )
    window_start = models.DateTimeField()
    request_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "window_start"],
                name="uniq_funded_chat_rate_user_window",
            )
        ]


class FundedChatRequest(models.Model):
    """One idempotent funded provider attempt; never stores raw provider errors."""

    STATUS_RESERVED = "reserved"
    STATUS_DISPATCHING = "dispatching"
    STATUS_PROVIDER_SUCCEEDED = "provider_succeeded"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_RECONCILIATION_REQUIRED = "reconcile_required"
    STATUS_RECONCILED = "reconciled"
    STATUS_ACCOUNTING_ANOMALY = "accounting_anomaly"
    STATUS_OPERATOR_REPAIR_REQUIRED = "operator_repair_required"
    STATUS_CHOICES = [
        (STATUS_RESERVED, "Reserved"),
        (STATUS_DISPATCHING, "Dispatching"),
        (STATUS_PROVIDER_SUCCEEDED, "Provider succeeded"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
        (STATUS_RECONCILIATION_REQUIRED, "Reconciliation required"),
        (STATUS_RECONCILED, "Reconciled conservatively"),
        (STATUS_ACCOUNTING_ANOMALY, "Accounting anomaly"),
        (STATUS_OPERATOR_REPAIR_REQUIRED, "Operator repair required"),
    ]

    PHASE_PRE_DISPATCH = "pre_dispatch"
    PHASE_DISPATCHED = "dispatched"
    PHASE_RESPONSE_RECEIVED = "response_received"
    PHASE_RECONCILED = "reconciled"
    PHASE_CHOICES = [
        (PHASE_PRE_DISPATCH, "Pre-dispatch"),
        (PHASE_DISPATCHED, "Provider dispatched"),
        (PHASE_RESPONSE_RECEIVED, "Provider response received"),
        (PHASE_RECONCILED, "Reconciled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="funded_chat_requests",
    )
    day = models.DateField()
    idempotency_key_hash = models.CharField(max_length=64)
    request_hash = models.CharField(max_length=64)
    provider = models.CharField(max_length=64)
    model = models.CharField(max_length=200)
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default=STATUS_RESERVED
    )
    phase = models.CharField(
        max_length=24, choices=PHASE_CHOICES, default=PHASE_PRE_DISPATCH
    )
    dispatch_key = models.CharField(
        max_length=64, unique=True, default=funded_dispatch_key, editable=False
    )
    lease_expires_at = models.DateTimeField(default=timezone.now)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    provider_responded_at = models.DateTimeField(null=True, blank=True)
    reconciliation_required_at = models.DateTimeField(null=True, blank=True)
    operator_repair_metadata = models.JSONField(default=dict, blank=True)
    reserved_subsidy_usd = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("0")
    )
    provider_prompt_tokens = models.PositiveIntegerField(default=0)
    provider_completion_tokens = models.PositiveIntegerField(default=0)
    provider_cost_usd = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("0")
    )
    subsidy_cost_usd = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("0")
    )
    response_text = models.TextField(blank=True, default="")
    error_category = models.CharField(max_length=32, blank=True, default="")
    retry_after_seconds = models.PositiveIntegerField(null=True, blank=True)
    support_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key_hash"],
                name="uniq_funded_chat_user_idempotency",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_subsidy_usd__gte=0),
                name="funded_request_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(provider_cost_usd__gte=0),
                name="funded_request_provider_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(subsidy_cost_usd__gte=0),
                name="funded_request_subsidy_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=["day", "provider", "status"]),
            models.Index(fields=["user", "day", "status"]),
        ]
