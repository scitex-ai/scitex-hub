#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew app models — Hash Registration for the Clew Registry."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class HashRegistration(models.Model):
    """A registered hash with server-side timestamp.

    The Clew Registry stores hashes with trusted server timestamps,
    proving "this data existed at this point in time."
    """

    hash = models.CharField(max_length=64, db_index=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hash_registrations",
    )
    source_type = models.CharField(
        max_length=20,
        default="manual",
        choices=[
            ("session", "Session"),
            ("file", "File"),
            ("stamp", "Stamp"),
            ("manual", "Manual"),
        ],
    )
    session_id = models.CharField(max_length=100, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-registered_at"]
        indexes = [
            models.Index(fields=["user", "-registered_at"]),
        ]
        unique_together = [("hash", "user")]

    def __str__(self):
        return f"{self.hash[:16]}... ({self.user}, {self.registered_at})"


# EOF
