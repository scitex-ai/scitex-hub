#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app admin - Repository sync model."""

from __future__ import annotations

from django.contrib import admin

from ..models import RepositorySync


@admin.register(RepositorySync)
class RepositorySyncAdmin(admin.ModelAdmin):
    list_display = [
        "sync_type",
        "target_display",
        "status",
        "progress_display",
        "started_at",
        "completed_at",
        "user",
    ]
    list_filter = [
        "sync_type",
        "status",
        "repository_connection__repository__repository_type",
        "started_at",
    ]
    search_fields = [
        "user__username",
        "dataset__title",
        "repository_connection__repository__name",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Sync Information",
            {
                "fields": (
                    "user",
                    "repository_connection",
                    "dataset",
                    "sync_type",
                    "status",
                )
            },
        ),
        (
            "Progress Tracking",
            {
                "fields": (
                    "total_items",
                    "completed_items",
                    "failed_items",
                    "total_bytes",
                    "transferred_bytes",
                )
            },
        ),
        ("Timing", {"fields": ("started_at", "completed_at", "estimated_completion")}),
        (
            "Results & Logs",
            {
                "fields": ("result_data", "error_message", "sync_log"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def target_display(self, obj):
        if obj.dataset:
            return f"Dataset: {obj.dataset.title[:30]}..."
        return f"Repository: {obj.repository_connection.repository.name}"

    target_display.short_description = "Target"

    def progress_display(self, obj):
        if obj.total_items > 0:
            percentage = (obj.completed_items / obj.total_items) * 100
            return f"{obj.completed_items}/{obj.total_items} ({percentage:.1f}%)"
        return "N/A"

    progress_display.short_description = "Progress"


# EOF
