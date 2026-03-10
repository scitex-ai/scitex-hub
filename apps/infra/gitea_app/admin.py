"""
Gitea App Admin Configuration
"""

from django.contrib import admin
from .models import GitFileStatus


@admin.register(GitFileStatus)
class GitFileStatusAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "file_path",
        "git_status",
        "last_modified_at",
        "file_size",
        "is_binary",
    )
    list_filter = ("git_status", "is_binary", "last_modified_at")
    search_fields = ("project__name", "file_path", "last_commit_hash")
    readonly_fields = ("last_modified_at",)

    def get_queryset(self, request):
        """Optimize query with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("project", "project__owner")
