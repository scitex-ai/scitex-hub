from django.contrib import admin
from .models import GlobalSearchQuery


@admin.register(GlobalSearchQuery)
class GlobalSearchQueryAdmin(admin.ModelAdmin):
    list_display = ("query", "search_type", "user", "results_count", "created_at")
    list_filter = ("search_type", "created_at")
    search_fields = ("query", "user__username")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
