from django.contrib import admin
from .models import IntegrationConnection, ORCIDProfile, SlackWebhook, IntegrationLog


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "service",
        "status",
        "external_username",
        "created_at",
        "last_sync_at",
    )
    list_filter = ("service", "status", "created_at")
    search_fields = ("user__username", "external_username", "external_user_id")
    readonly_fields = ("created_at", "updated_at", "last_sync_at")

    fieldsets = (
        ("Basic Info", {"fields": ("user", "service", "status")}),
        (
            "External Service",
            {"fields": ("external_user_id", "external_username", "metadata")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_sync_at")}),
    )


@admin.register(ORCIDProfile)
class ORCIDProfileAdmin(admin.ModelAdmin):
    list_display = (
        "orcid_id",
        "get_full_name",
        "current_institution",
        "last_synced_at",
    )
    search_fields = ("orcid_id", "given_names", "family_name", "current_institution")
    readonly_fields = ("last_synced_at",)


@admin.register(SlackWebhook)
class SlackWebhookAdmin(admin.ModelAdmin):
    list_display = (
        "connection",
        "channel",
        "is_active",
        "notification_count",
        "last_notification_at",
    )
    list_filter = ("is_active", "created_at")
    readonly_fields = ("created_at", "last_notification_at", "notification_count")
    filter_horizontal = ("project_filter",)


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ("connection", "action", "success", "created_at")
    list_filter = ("action", "success", "created_at")
    search_fields = ("connection__user__username", "details", "error_message")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
