from django.contrib import admin
from ..models import CompilationJob, AIAssistanceLog


@admin.register(CompilationJob)
class CompilationJobAdmin(admin.ModelAdmin):
    list_display = ["job_id", "manuscript", "status", "compilation_type", "created_at"]
    search_fields = ["manuscript__title"]
    list_filter = ["status", "compilation_type", "created_at"]
    readonly_fields = ["job_id", "created_at"]


@admin.register(AIAssistanceLog)
class AIAssistanceLogAdmin(admin.ModelAdmin):
    list_display = ["assistance_type", "manuscript", "user", "created_at"]
    search_fields = ["manuscript__title", "user__username"]
    list_filter = ["assistance_type", "created_at"]
