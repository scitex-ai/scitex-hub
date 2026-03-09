from django.db import models
from django.contrib.auth.models import User
import uuid


class SearchQuery(models.Model):
    """Track user searches"""

    SEARCH_TYPE_CHOICES = [
        ("simple", "Simple Search"),
        ("advanced", "Advanced Search"),
        ("author", "Author Search"),
        ("citation", "Citation Search"),
        ("semantic", "Semantic Search"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="search_queries"
    )
    query_text = models.TextField()
    search_type = models.CharField(
        max_length=20, choices=SEARCH_TYPE_CHOICES, default="simple"
    )
    filters = models.JSONField(default=dict, blank=True)  # Store applied filters
    result_count = models.IntegerField(default=0)
    execution_time = models.FloatField(null=True, blank=True)  # in seconds
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.query_text[:50]}"


class SearchResult(models.Model):
    """Store search results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_query = models.ForeignKey(
        SearchQuery, on_delete=models.CASCADE, related_name="results"
    )
    paper = models.ForeignKey("SearchIndex", on_delete=models.CASCADE)
    rank = models.IntegerField()
    score = models.FloatField()  # Relevance score
    snippet = models.TextField(blank=True)  # Highlighted snippet
    clicked = models.BooleanField(default=False)
    click_timestamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["search_query", "rank"]
        indexes = [
            models.Index(fields=["search_query", "rank"]),
        ]

    def __str__(self):
        return f"Result {self.rank} for query {self.search_query.id}"


class SearchFilter(models.Model):
    """Advanced search filters"""

    FILTER_TYPE_CHOICES = [
        ("date_range", "Date Range"),
        ("author", "Author"),
        ("journal", "Journal"),
        ("topic", "Topic"),
        ("citation_count", "Citation Count"),
        ("document_type", "Document Type"),
        ("open_access", "Open Access"),
        ("language", "Language"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPE_CHOICES)
    description = models.TextField(blank=True)
    configuration = models.JSONField(default=dict)  # Store filter-specific config
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["filter_type", "name"]

    def __str__(self):
        return f"{self.filter_type}: {self.name}"


class SavedSearch(models.Model):
    """User's saved searches"""

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("never", "Never"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_searches"
    )
    name = models.CharField(max_length=200)
    query_text = models.TextField()
    search_type = models.CharField(
        max_length=20, choices=SearchQuery.SEARCH_TYPE_CHOICES
    )
    filters = models.JSONField(default=dict, blank=True)
    email_alerts = models.BooleanField(default=False)
    alert_frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default="never"
    )
    last_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.user.username}: {self.name}"
