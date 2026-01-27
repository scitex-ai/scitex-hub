#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app admin - Repository models."""

from __future__ import annotations

from django.contrib import admin

from ..models import Repository, RepositoryConnection


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "repository_type",
        "status",
        "supports_doi",
        "is_default",
        "total_deposits",
        "active_connections",
    ]
    list_filter = [
        "repository_type",
        "status",
        "supports_doi",
        "is_open_access",
        "is_default",
    ]
    search_fields = ["name", "description", "api_base_url"]
    ordering = ["name"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "repository_type", "description", "status")},
        ),
        (
            "API Configuration",
            {
                "fields": (
                    "api_base_url",
                    "api_version",
                    "api_documentation_url",
                    "website_url",
                )
            },
        ),
        (
            "Features & Capabilities",
            {
                "fields": (
                    "supports_doi",
                    "supports_versioning",
                    "supports_private_datasets",
                    "max_file_size_mb",
                    "max_dataset_size_mb",
                    "requires_authentication",
                )
            },
        ),
        (
            "Metadata & Formats",
            {
                "fields": (
                    "supports_metadata_formats",
                    "supported_file_formats",
                    "license_options",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Repository Settings", {"fields": ("is_open_access", "is_default")}),
        (
            "Statistics",
            {
                "fields": ("total_deposits", "active_connections"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(RepositoryConnection)
class RepositoryConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "repository",
        "connection_name",
        "status",
        "last_verified",
        "total_deposits",
    ]
    list_filter = [
        "status",
        "repository__repository_type",
        "is_default",
        "auto_sync_enabled",
    ]
    search_fields = [
        "user__username",
        "repository__name",
        "connection_name",
        "username",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Connection Details",
            {"fields": ("user", "repository", "connection_name", "status")},
        ),
        (
            "Authentication",
            {
                "fields": ("username", "api_token", "oauth_token"),
                "description": "Sensitive credentials are encrypted in storage",
            },
        ),
        (
            "Settings",
            {"fields": ("is_default", "auto_sync_enabled", "notification_enabled")},
        ),
        (
            "Status Information",
            {
                "fields": ("last_verified", "expires_at", "last_activity"),
                "classes": ("collapse",),
            },
        ),
        (
            "Usage Statistics",
            {"fields": ("total_deposits", "total_downloads"), "classes": ("collapse",)},
        ),
        (
            "Error Tracking",
            {"fields": ("last_error", "error_count"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["last_verified", "last_activity", "error_count"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


# EOF
