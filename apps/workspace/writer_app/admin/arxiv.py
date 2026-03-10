from django.contrib import admin
from ..models import ArxivSubmission, ArxivAccount


@admin.register(ArxivSubmission)
class ArxivSubmissionAdmin(admin.ModelAdmin):
    list_display = ["title", "arxiv_id", "status", "user", "submitted_at"]
    search_fields = ["title", "arxiv_id"]
    list_filter = ["status", "submission_type", "submitted_at"]


@admin.register(ArxivAccount)
class ArxivAccountAdmin(admin.ModelAdmin):
    list_display = ["arxiv_username", "user", "is_verified", "is_active"]
    search_fields = ["arxiv_username", "user__username"]
    list_filter = ["is_verified", "is_active"]
