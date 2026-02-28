#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marketplace admin configuration."""

from django.contrib import admin

from .models import (
    AppsModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
    ModuleVersion,
)


@admin.register(AppsModule)
class AppsModuleAdmin(admin.ModelAdmin):
    list_display = (
        "module_name",
        "category",
        "author",
        "star_count",
        "install_count",
        "avg_rating",
        "is_builtin",
        "is_verified",
    )
    list_filter = ("category", "is_builtin", "is_featured", "is_verified", "visibility")
    search_fields = ("module_name", "short_description")
    readonly_fields = (
        "created_at",
        "updated_at",
        "star_count",
        "install_count",
        "avg_rating",
    )


@admin.register(ModuleVersion)
class ModuleVersionAdmin(admin.ModelAdmin):
    list_display = ("module", "version", "is_stable", "released_at")
    list_filter = ("is_stable",)


@admin.register(ModuleInstallation)
class ModuleInstallationAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "is_enabled", "tab_order", "installed_at")
    list_filter = ("is_enabled",)
    search_fields = ("user__username", "module__module_name")


@admin.register(ModuleStar)
class ModuleStarAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "starred_at")


@admin.register(ModuleReview)
class ModuleReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "rating", "title", "created_at")
    list_filter = ("rating",)


from .models import ModuleSubmission  # noqa: E402


@admin.register(ModuleSubmission)
class ModuleSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "module",
        "submitted_by",
        "status",
        "reviewer",
        "submitted_at",
        "reviewed_at",
    )
    list_filter = ("status",)
    search_fields = ("module__module_name", "submitted_by__username")
    readonly_fields = ("submitted_at",)
    actions = ["approve_submissions", "reject_submissions"]

    @admin.action(description="Approve selected submissions")
    def approve_submissions(self, request, queryset):
        from django.utils import timezone

        for sub in queryset.filter(status="pending"):
            sub.status = "approved"
            sub.reviewer = request.user
            sub.reviewed_at = timezone.now()
            sub.save(update_fields=["status", "reviewer", "reviewed_at"])
            sub.module.visibility = "public"
            sub.module.is_verified = True
            sub.module.save(update_fields=["visibility", "is_verified"])

    @admin.action(description="Reject selected submissions")
    def reject_submissions(self, request, queryset):
        from django.utils import timezone

        queryset.filter(status="pending").update(
            status="rejected", reviewer=request.user, reviewed_at=timezone.now()
        )


# EOF
