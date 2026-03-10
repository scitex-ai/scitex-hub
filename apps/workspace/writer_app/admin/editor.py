from django.contrib import admin
from ..models import Manuscript


@admin.register(Manuscript)
class ManuscriptAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "created_at", "updated_at"]
    search_fields = ["title", "description"]
    list_filter = ["created_at", "owner"]
    readonly_fields = ["created_at", "updated_at"]
