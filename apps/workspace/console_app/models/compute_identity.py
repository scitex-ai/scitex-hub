"""Stable POSIX identity a hub user's SLURM jobs run as on the compute nodes."""

from django.conf import settings
from django.db import models


class ComputeIdentity(models.Model):
    # SET_NULL keeps the row after the user is deleted, so the uid stays
    # claimed and is never handed to someone who could read the old files.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="compute_identity",
    )
    username = models.CharField(max_length=150, db_index=True)
    uid = models.PositiveIntegerField(unique=True)
    gid = models.PositiveIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uid"]

    def __str__(self):
        return f"{self.username} uid={self.uid} gid={self.gid}"
