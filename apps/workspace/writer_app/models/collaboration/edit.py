"""CollaborativeEdit model for tracking real-time document changes."""

import uuid

from django.db import models


class CollaborativeEdit(models.Model):
    """Track individual editing operations in collaborative sessions."""

    OPERATION_CHOICES = [
        ("insert", "Insert"),
        ("delete", "Delete"),
        ("retain", "Retain"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manuscript = models.ForeignKey(
        "writer_app.Manuscript",
        on_delete=models.CASCADE,
        related_name="collaborative_edits",
    )
    session = models.ForeignKey(
        "writer_app.CollaborativeSession",
        on_delete=models.CASCADE,
        related_name="edits",
    )
    section_id = models.CharField(max_length=100)
    operation_type = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    operation_data = models.JSONField()
    version = models.IntegerField()
    client_version = models.IntegerField()
    was_transformed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version"]
        indexes = [
            models.Index(fields=["manuscript", "section_id", "version"]),
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self):
        return f"{self.operation_type} v{self.version} in {self.section_id}"
