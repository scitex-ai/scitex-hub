import uuid

from django.conf import settings
from django.db import models


class AppData(models.Model):
    """Generic data store for user app schemas.

    Instead of creating Django models per user app, all app data
    is stored in this single table with JSONField for flexible schemas.
    Indexed virtual columns enable fast queries on common fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_name = models.CharField(max_length=100, db_index=True)
    schema_name = models.CharField(max_length=100, db_index=True)
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="app_data",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="app_data",
    )
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Indexed virtual columns for fast queries on common field patterns
    idx_string_1 = models.CharField(
        max_length=500, db_index=True, null=True, blank=True
    )
    idx_string_2 = models.CharField(
        max_length=500, db_index=True, null=True, blank=True
    )
    idx_integer_1 = models.IntegerField(db_index=True, null=True, blank=True)
    idx_integer_2 = models.IntegerField(db_index=True, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["app_name", "schema_name", "project"]),
            models.Index(fields=["app_name", "schema_name", "owner"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.app_name}.{self.schema_name}:{self.id}"
