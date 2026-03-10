from django.db import models
from django.contrib.auth.models import User


class GlobalSearchQuery(models.Model):
    """
    Track global search queries for analytics and autocomplete suggestions.
    Different from scholar_app.SearchQuery which is paper-specific.
    """

    query = models.CharField(max_length=200)
    search_type = models.CharField(
        max_length=20,
        choices=[
            ("all", "All"),
            ("users", "Users"),
            ("repositories", "Repositories"),
            ("code", "Code"),
            ("papers", "Papers"),
        ],
        default="all",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="global_search_queries",
    )
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.query} ({self.search_type})"

    @classmethod
    def get_popular_queries(cls, limit=10):
        """Get most popular search queries"""
        from django.db.models import Count

        return (
            cls.objects.values("query")
            .annotate(count=Count("query"))
            .order_by("-count")[:limit]
        )
