"""
Django admin configuration for organizations_app.
"""

from django.contrib import admin

from .models import (
    Organization,
    OrganizationMembership,
    ResearchGroup,
    ResearchGroupMembership,
)


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["user"]


class ResearchGroupInline(admin.TabularInline):
    model = ResearchGroup
    extra = 0
    fields = ["name", "leader", "description"]
    autocomplete_fields = ["leader"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "website", "member_count", "created_at"]
    search_fields = ["name", "slug", "description"]
    list_filter = ["created_at"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrganizationMembershipInline, ResearchGroupInline]

    def member_count(self, obj):
        return obj.members.count()

    member_count.short_description = "Members"


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role", "joined_at"]
    list_filter = ["role", "joined_at"]
    search_fields = ["user__username", "organization__name"]
    autocomplete_fields = ["user", "organization"]


class ResearchGroupMembershipInline(admin.TabularInline):
    model = ResearchGroupMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(ResearchGroup)
class ResearchGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "leader", "member_count", "created_at"]
    list_filter = ["organization", "created_at"]
    search_fields = ["name", "description", "organization__name"]
    autocomplete_fields = ["organization", "leader"]
    inlines = [ResearchGroupMembershipInline]

    def member_count(self, obj):
        return obj.members.count()

    member_count.short_description = "Members"


@admin.register(ResearchGroupMembership)
class ResearchGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "group", "role", "is_active", "joined_at"]
    list_filter = [
        "role",
        "is_active",
        "can_create_projects",
        "can_invite_collaborators",
    ]
    search_fields = ["user__username", "group__name"]
    autocomplete_fields = ["user", "group"]
