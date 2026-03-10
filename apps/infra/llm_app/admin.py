from django.contrib import admin

from .models import LLMConnection, LLMUsageLog


@admin.register(LLMConnection)
class LLMConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "connection",
        "default_model",
        "total_requests",
        "total_tokens_used",
        "estimated_cost_usd",
        "last_request_at",
    ]
    list_filter = ["connection__service", "connection__status"]
    search_fields = ["connection__user__username", "default_model"]
    readonly_fields = [
        "total_tokens_used",
        "total_requests",
        "estimated_cost_usd",
        "last_request_at",
        "created_at",
        "updated_at",
    ]


@admin.register(LLMUsageLog)
class LLMUsageLogAdmin(admin.ModelAdmin):
    list_display = [
        "connection",
        "app_name",
        "feature",
        "model_used",
        "total_tokens",
        "estimated_cost_usd",
        "success",
        "created_at",
    ]
    list_filter = ["app_name", "success", "model_used"]
    search_fields = ["connection__user__username", "feature"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]
