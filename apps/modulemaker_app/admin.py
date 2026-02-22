#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Maker admin configuration."""

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
        "updated_at",
    )
    list_filter = ("category", "visibility", "is_active")
    search_fields = ("slug", "label", "author__username", "description")
    readonly_fields = ("created_at", "updated_at", "run_count", "last_run_at")


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
