from django.contrib import admin
from ..models import ManuscriptVersion, ManuscriptBranch


@admin.register(ManuscriptVersion)
class ManuscriptVersionAdmin(admin.ModelAdmin):
    list_display = [
        "version_number",
        "manuscript",
        "branch_name",
        "created_by",
        "created_at",
    ]
    search_fields = ["manuscript__title", "version_number"]
    list_filter = ["branch_name", "created_at"]


@admin.register(ManuscriptBranch)
class ManuscriptBranchAdmin(admin.ModelAdmin):
    list_display = ["name", "manuscript", "created_by", "is_active", "created_at"]
    search_fields = ["manuscript__title", "name"]
    list_filter = ["is_active", "created_at"]
