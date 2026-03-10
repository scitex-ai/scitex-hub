#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app admin - Dataset models."""

from __future__ import annotations

from django.contrib import admin

from ..models import Dataset, DatasetFile, DatasetVersion


class DatasetFileInline(admin.TabularInline):
    model = DatasetFile
    extra = 0
    fields = ["filename", "file_type", "file_format", "size_display", "download_count"]
    readonly_fields = ["size_display"]

    def size_display(self, obj):
        return obj.get_size_display() if obj.pk else ""

    size_display.short_description = "Size"


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "owner",
        "dataset_type",
        "status",
        "visibility",
        "file_count",
        "size_display",
        "repository_name",
        "created_at",
    ]
    list_filter = [
        "dataset_type",
        "status",
        "visibility",
        "repository_connection__repository__repository_type",
        "created_at",
        "published_at",
    ]
    search_fields = [
        "title",
        "description",
        "keywords",
        "owner__username",
        "repository_id",
    ]
    ordering = ["-created_at"]
    inlines = [DatasetFileInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "dataset_type", "keywords")},
        ),
        ("Ownership & Collaboration", {"fields": ("owner", "collaborators")}),
        (
            "Repository Information",
            {
                "fields": (
                    "repository_connection",
                    "repository_id",
                    "repository_url",
                    "repository_doi",
                    "version",
                )
            },
        ),
        (
            "Status & Visibility",
            {
                "fields": (
                    "status",
                    "visibility",
                    "license",
                    "access_conditions",
                    "embargo_until",
                )
            },
        ),
        (
            "Research Context",
            {
                "fields": (
                    "project",
                    "related_papers",
                    "generated_by_job",
                    "associated_notebooks",
                    "cited_in_manuscripts",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "File Information",
            {
                "fields": ("file_count", "total_size_bytes", "file_formats"),
                "classes": ("collapse",),
            },
        ),
        (
            "Usage Statistics",
            {
                "fields": ("download_count", "citation_count", "view_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at", "published_at", "last_synced"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "file_count", "total_size_bytes"]
    filter_horizontal = [
        "collaborators",
        "related_papers",
        "associated_notebooks",
        "cited_in_manuscripts",
    ]

    def repository_name(self, obj):
        return obj.repository_connection.repository.name

    repository_name.short_description = "Repository"

    def size_display(self, obj):
        return obj.get_file_size_display()

    size_display.short_description = "Total Size"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "owner",
                "repository_connection__repository",
                "project",
                "generated_by_job",
            )
            .prefetch_related("collaborators")
        )


@admin.register(DatasetFile)
class DatasetFileAdmin(admin.ModelAdmin):
    list_display = [
        "filename",
        "dataset_title",
        "file_type",
        "file_format",
        "size_display",
        "download_count",
    ]
    list_filter = ["file_type", "file_format", "created_at"]
    search_fields = ["filename", "dataset__title", "description"]
    ordering = ["-created_at"]

    def dataset_title(self, obj):
        return obj.dataset.title

    dataset_title.short_description = "Dataset"

    def size_display(self, obj):
        return obj.get_size_display()

    size_display.short_description = "Size"


@admin.register(DatasetVersion)
class DatasetVersionAdmin(admin.ModelAdmin):
    list_display = [
        "dataset_title",
        "version_number",
        "is_current",
        "files_added",
        "files_modified",
        "created_at",
    ]
    list_filter = ["is_current", "created_at"]
    search_fields = ["dataset__title", "version_number", "version_description"]
    ordering = ["-created_at"]

    def dataset_title(self, obj):
        return obj.dataset.title

    dataset_title.short_description = "Dataset"


# EOF
