from django.contrib import admin

from .models import (
    BillingAccountEvent,
    BillingAccountState,
    SpendAlert,
    SpendControl,
)


@admin.register(SpendControl)
class SpendControlAdmin(admin.ModelAdmin):
    list_display = ("user", "monthly_cap_usd", "updated_at")
    search_fields = ("user__username", "user__email")


@admin.register(SpendAlert)
class SpendAlertAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "period",
        "threshold",
        "spend_usd",
        "cap_usd",
        "created_at",
        "emailed_at",
    )
    list_filter = ("period", "threshold")
    search_fields = ("user__username",)


@admin.register(BillingAccountState)
class BillingAccountStateAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "state",
        "past_due_since",
        "grace_until",
        "reminders_sent",
        "cancelled_at",
    )
    list_filter = ("state",)
    search_fields = ("user__username",)


@admin.register(BillingAccountEvent)
class BillingAccountEventAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "kind",
        "from_state",
        "to_state",
        "provider_event_id",
        "created_at",
    )
    list_filter = ("kind",)
    search_fields = ("user__username", "provider_event_id")

    def has_change_permission(self, request, obj=None):
        return False  # append-only

    def has_delete_permission(self, request, obj=None):
        return False

