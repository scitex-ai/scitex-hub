#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Maker admin configuration."""

from __future__ import annotations

from django.contrib import admin

from .models import ModuleExecution, UserModule


@admin.register(UserModule)
class UserModuleAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "label",
        "author",
        "category",
        "visibility",
        "is_active",
        "run_count",
        "is_git_sourced",
        "updated_at",
    )
    list_filter = ("category", "visibility", "is_active")
    search_fields = ("slug", "label", "author__username", "description")
    readonly_fields = (
        "created_at",
        "updated_at",
        "run_count",
        "last_run_at",
        "is_git_sourced",
    )

    @admin.display(boolean=True, description="Git Source")
    def is_git_sourced(self, obj):
        return obj.is_git_sourced


@admin.register(ModuleExecution)
class ModuleExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "module",
        "user",
        "status",
        "wall_time_ms",
        "peak_memory_mb",
        "started_at",
    )
    list_filter = ("status",)
    search_fields = ("module__slug", "user__username")
    readonly_fields = ("started_at",)


# EOF
