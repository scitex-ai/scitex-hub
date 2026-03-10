from django.contrib import admin
from .models import Manuscript


@admin.register(Manuscript)
class ManuscriptAdmin(admin.ModelAdmin):
    """Minimal manuscript admin - links projects to scitex.writer.Writer."""

    list_display = ["title", "owner", "project", "writer_initialized", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["title", "project__name", "owner__username"]
    readonly_fields = ["created_at", "updated_at"]
