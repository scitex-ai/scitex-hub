#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 17:45:00 (ywatanabe)"
# File: ./apps/workspace_app/admin.py

from django.contrib import admin
from django.contrib import messages
from .models import UserWorkspace

# Temporarily disabled due to missing docker dependency
try:
    from .services import UserContainerManager

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    UserContainerManager = None


@admin.register(UserWorkspace)
class UserWorkspaceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "is_running",
        "container_name",
        "last_activity_at",
        "cpu_limit_display",
        "memory_limit_display",
        "created_at",
    ]
    list_filter = ["is_running", "created_at"]
    search_fields = ["user__username", "container_name"]
    readonly_fields = [
        "container_id",
        "last_started_at",
        "last_stopped_at",
        "last_activity_at",
        "created_at",
        "updated_at",
    ]
    actions = [
        "start_containers",
        "stop_containers",
        "remove_containers",
        "cleanup_idle",
    ]

    def cpu_limit_display(self, obj):
        """Display CPU limit in cores"""
        return f"{obj.cpu_limit / 100000:.1f} cores"

    cpu_limit_display.short_description = "CPU Limit"

    def memory_limit_display(self, obj):
        """Display memory limit in GB"""
        return f"{obj.memory_limit / (1024**3):.1f} GB"

    memory_limit_display.short_description = "Memory Limit"

    @admin.action(description="Start selected user containers")
    def start_containers(self, request, queryset):
        """Start containers for selected users"""
        if not DOCKER_AVAILABLE:
            messages.error(request, "Docker support not available")
            return

        manager = UserContainerManager()
        started = 0
        for workspace in queryset:
            try:
                manager.get_or_create_container(workspace.user)
                started += 1
            except Exception as e:
                messages.error(
                    request,
                    f"Failed to start container for {workspace.user.username}: {e}",
                )

        if started:
            messages.success(request, f"Started {started} container(s)")

    @admin.action(description="Stop selected user containers")
    def stop_containers(self, request, queryset):
        """Stop containers for selected users"""
        if not DOCKER_AVAILABLE:
            messages.error(request, "Docker support not available")
            return

        manager = UserContainerManager()
        stopped = 0
        for workspace in queryset.filter(is_running=True):
            try:
                if manager.stop_container(workspace.user):
                    stopped += 1
            except Exception as e:
                messages.error(
                    request,
                    f"Failed to stop container for {workspace.user.username}: {e}",
                )

        if stopped:
            messages.success(request, f"Stopped {stopped} container(s)")

    @admin.action(description="Remove selected user containers")
    def remove_containers(self, request, queryset):
        """Remove containers for selected users (WARNING: Data persists but container removed)"""
        if not DOCKER_AVAILABLE:
            messages.error(request, "Docker support not available")
            return

        manager = UserContainerManager()
        removed = 0
        for workspace in queryset:
            try:
                if manager.remove_container(workspace.user, force=True):
                    removed += 1
            except Exception as e:
                messages.error(
                    request,
                    f"Failed to remove container for {workspace.user.username}: {e}",
                )

        if removed:
            messages.success(request, f"Removed {removed} container(s)")

    @admin.action(description="Cleanup idle containers (30+ min)")
    def cleanup_idle(self, request, queryset):
        """Stop containers idle for 30+ minutes"""
        if not DOCKER_AVAILABLE:
            messages.error(request, "Docker support not available")
            return

        manager = UserContainerManager()
        stopped = manager.cleanup_idle_containers(idle_minutes=30)
        messages.success(request, f"Stopped {stopped} idle container(s)")


# EOF
