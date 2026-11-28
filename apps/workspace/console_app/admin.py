from django.contrib import admin

from .models import WorkloadSession


@admin.register(WorkloadSession)
class WorkloadSessionAdmin(admin.ModelAdmin):
    """Read-only: rows are launch/billing records written by the launchers."""

    list_display = (
        "user",
        "workload",
        "scheduler",
        "scheduler_job_id",
        "cpus",
        "memory_gb",
        "started_at",
        "stopped_at",
        "stop_reason",
    )
    list_filter = ("workload", "scheduler", "stop_reason")
    search_fields = ("user__username", "scheduler_job_id", "session_id")

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
