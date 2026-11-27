from django.contrib import admin

from .models import (
    APIKey,
    CloudResource,
    Contributor,
    ServiceIntegration,
    Subscription,
    SubscriptionPlan,
)

# EmailVerification admin now in apps.infra.auth_app.admin


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "plan_type",
        "price_monthly",
        "max_projects",
        "storage_gb",
        "is_featured",
        "is_active",
    ]
    list_filter = ["plan_type", "is_featured", "is_active"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "plan_type",
                    "price_monthly",
                    "price_yearly",
                    "is_featured",
                    "is_active",
                    "display_order",
                )
            },
        ),
        (
            "Resource Limits",
            {"fields": ("max_projects", "storage_gb", "cpu_cores", "gpu_vram_gb")},
        ),
        (
            "Feature Flags",
            {
                "fields": (
                    "has_watermark",
                    "requires_citation",
                    "requires_archive",
                    "has_priority_support",
                    "has_custom_integrations",
                    "has_team_collaboration",
                )
            },
        ),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "plan",
        "status",
        "current_period_start",
        "current_period_end",
    ]
    list_filter = ["status", "plan", "created_at"]
    search_fields = ["user__username", "user__email", "stripe_subscription_id"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(CloudResource)
class CloudResourceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "resource_type",
        "amount_used",
        "unit",
        "period_start",
        "created_at",
    ]
    list_filter = ["resource_type", "created_at"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "prefix", "is_active", "last_used", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["user__username", "user__email", "name", "prefix"]
    readonly_fields = ["key", "prefix", "created_at", "last_used"]
    fieldsets = (
        ("Basic Information", {"fields": ("user", "name", "key", "prefix")}),
        (
            "Permissions",
            {"fields": ("can_read", "can_write", "can_delete", "rate_limit_per_hour")},
        ),
        ("Status", {"fields": ("is_active", "last_used", "expires_at")}),
    )


@admin.register(ServiceIntegration)
class ServiceIntegrationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "integration_type",
        "is_active",
        "last_synced",
        "created_at",
    ]
    list_filter = ["integration_type", "is_active", "created_at"]
    search_fields = ["user__username", "user__email", "external_id"]
    readonly_fields = ["created_at", "updated_at"]
    exclude = ["access_token", "refresh_token"]  # Hide sensitive fields


@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = [
        "github_username",
        "name",
        "role",
        "is_core_team",
        "contributions",
        "display_order",
        "updated_at",
    ]
    list_filter = ["role", "is_core_team", "created_at"]
    search_fields = ["github_username", "name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("github_username", "name", "avatar_url", "github_url")},
        ),
        ("Role and Status", {"fields": ("role", "is_core_team", "display_order")}),
        (
            "Contributions",
            {
                "fields": (
                    "contributions",
                    "contributions_description",
                    "first_contribution",
                    "last_contribution",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


from .models import Publication, ServiceInquiry  # noqa: E402


class InquiryStatusFilter(admin.SimpleListFilter):
    """Open inquiries first: the list opens on what still needs a reply."""

    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [("open", "Open"), ("handled", "Handled"), ("all", "All")]

    def choices(self, changelist):
        # "Open" is the default, so the built-in "All" entry is replaced by ours.
        for value, label in self.lookup_choices:
            yield {
                "selected": (self.value() or "open") == value,
                "query_string": changelist.get_query_string({self.parameter_name: value}),
                "display": label,
            }

    def queryset(self, request, queryset):
        value = self.value() or "open"
        if value == "open":
            return queryset.filter(handled=False)
        if value == "handled":
            return queryset.filter(handled=True)
        return queryset


@admin.register(ServiceInquiry)
class ServiceInquiryAdmin(admin.ModelAdmin):
    """The inquiry inbox (scitex-hub#1235): open first, with who/when handled.

    The list opens on OPEN inquiries. "Notified" shows whether the operator
    notification was delivered, so a lead that nobody was told about is
    visible as such rather than looking like one that was ignored.
    """

    list_display = [
        "name",
        "affiliation",
        "budget",
        "created_at",
        "notified",
        "handled",
        "handled_at",
        "handled_by",
        "first_response",
    ]
    list_filter = [InquiryStatusFilter, "created_at"]
    search_fields = ["name", "affiliation", "request"]
    readonly_fields = [
        "name",
        "affiliation",
        "request",
        "budget",
        "created_at",
        "handled_at",
        "handled_by",
        "notified_at",
        "notify_error",
    ]
    fields = readonly_fields[:5] + ["handled"] + readonly_fields[5:]
    date_hierarchy = "created_at"
    actions = ["mark_handled", "reopen"]

    @admin.display(description="Notified", boolean=True)
    def notified(self, obj):
        return obj.notified_at is not None

    @admin.display(description="First response")
    def first_response(self, obj):
        delta = obj.first_response_time
        if delta is None:
            return "-"
        hours = delta.total_seconds() / 3600
        return f"{hours / 24:.1f} d" if hours >= 48 else f"{hours:.1f} h"

    @admin.action(description="Mark selected inquiries as handled")
    def mark_handled(self, request, queryset):
        rows = list(queryset.filter(handled=False))
        for inquiry in rows:
            inquiry.mark_handled(request.user)
        self.message_user(request, f"{len(rows)} inquiry(ies) marked handled.")

    @admin.action(description="Reopen selected inquiries")
    def reopen(self, request, queryset):
        rows = list(queryset.filter(handled=True))
        for inquiry in rows:
            inquiry.reopen()
        self.message_user(request, f"{len(rows)} inquiry(ies) reopened.")

    def save_model(self, request, obj, form, change):
        # Ticking "handled" on the change form records who did it.
        if obj.handled and obj.handled_by is None:
            obj.handled_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = [
        "title_short",
        "year",
        "status",
        "is_active",
        "display_order",
        "updated_at",
    ]
    list_filter = ["status", "is_active", "year"]
    search_fields = ["title", "authors", "doi", "journal"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["is_active", "display_order"]
    fieldsets = (
        ("Identifiers", {"fields": ("doi",)}),
        (
            "Metadata",
            {"fields": ("title", "authors", "journal", "year", "volume", "page")},
        ),
        ("Content", {"fields": ("abstract",)}),
        ("URLs", {"fields": ("paper_url", "code_url")}),
        (
            "Display",
            {"fields": ("status", "is_featured", "is_active", "display_order")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Title")
    def title_short(self, obj):
        return obj.title[:60] + "..." if len(obj.title) > 60 else obj.title
