#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marketplace admin configuration."""

from django.contrib import admin

from .models import (
    MarketplaceModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
    ModuleVersion,
)


@admin.register(MarketplaceModule)
class MarketplaceModuleAdmin(admin.ModelAdmin):
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


# EOF
