import uuid

from django.contrib.auth.models import User
from django.db import models


class SavedGraph(models.Model):
    """Persisted citation graph with layout and rebuild recipe."""

    SOURCE_TYPE_CHOICES = [
        ("dois", "DOI List"),
        ("query", "Search Query"),
        ("library", "Library Papers"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_graphs"
    )
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saved_graphs",
    )
    name = models.CharField(max_length=200)
    source_type = models.CharField(
        max_length=10, choices=SOURCE_TYPE_CHOICES, default="dois"
    )

    # Recipe for rebuilding
    seed_dois = models.JSONField(default=list, blank=True)
    query_text = models.CharField(max_length=500, blank=True, default="")
    build_params = models.JSONField(default=dict, blank=True)

    # Snapshot data
    graph_data = models.JSONField(default=dict)
    node_positions = models.JSONField(default=dict, blank=True)

    # Summary stats (avoids loading full graph_data for list views)
    node_count = models.IntegerField(default=0)
    edge_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["user", "name"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.name} ({self.node_count} nodes)"
