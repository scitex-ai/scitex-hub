from django.contrib import admin

from .models import (
    APIKey,
    CloudResource,
    Contributor,
    DiscountAppeal,
    ServiceIntegration,
    Subscription,
    SubscriptionPlan,
    UserDiscount,
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


@admin.register(ServiceInquiry)
class ServiceInquiryAdmin(admin.ModelAdmin):
    """Read services-page inquiries here until a dedicated inbox is decided."""

    list_display = ["name", "affiliation", "budget", "handled", "created_at"]
    list_filter = ["handled", "created_at"]
    search_fields = ["name", "affiliation", "request"]
    list_editable = ["handled"]
    readonly_fields = ["name", "affiliation", "request", "budget", "created_at"]
    date_hierarchy = "created_at"


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


@admin.register(DiscountAppeal)
class DiscountAppealAdmin(admin.ModelAdmin):
    """The academic-appeal review queue (operator CCT4558).

    Approve issues the UserDiscount grant through the same audited path as
    the code (``grant_approved_appeal``); reject records a note the
    requester can read on the appeal page. See docs/product/ACADEMIC_DISCOUNT.md
    for reviewer best practice.
    """

    list_display = [
        "user",
        "institution",
        "claimed_email",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["institution", "claimed_email", "user__username"]
    readonly_fields = [
        "user",
        "claimed_email",
        "institution",
        "evidence",
        "decided_by",
        "decided_at",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
    actions = ["approve_appeals", "reject_appeals"]

    @admin.action(description="Approve — verify affiliation, issue grant")
    def approve_appeals(self, request, queryset):
        from apps.infra.public_app.services.academic_discount import (
            grant_approved_appeal,
        )

        approved, skipped = 0, 0
        for appeal in queryset.filter(status=DiscountAppeal.Status.OPEN):
            try:
                grant_approved_appeal(appeal, by_user=request.user)
            except ValueError as exc:
                skipped += 1
                self.message_user(request, f"#{appeal.pk}: {exc}")
            else:
                approved += 1
        self.message_user(
            request, f"Approved {approved}, skipped {skipped}."
        )

    @admin.action(description="Reject selected open appeals")
    def reject_appeals(self, request, queryset):
        # Note: the per-row reviewer_note is edited on the appeal itself
        # (it stays editable); the action only moves OPEN rows to REJECTED
        # so a note written first is never silently dropped by a bulk pass.
        from django.utils import timezone

        rejected = queryset.filter(status=DiscountAppeal.Status.OPEN).update(
            status=DiscountAppeal.Status.REJECTED,
            decided_by=request.user,
            decided_at=timezone.now(),
        )
        self.message_user(request, f"Rejected {rejected}.")


@admin.register(UserDiscount)
class UserDiscountAdmin(admin.ModelAdmin):
    """Issued grants, read-mostly: the appeal link answers "why $19"."""

    list_display = [
        "user",
        "code",
        "status",
        "verified_email",
        "basis_domain",
        "appeal",
    ]
    list_filter = ["status", "code"]
    search_fields = ["user__username", "verified_email", "basis_domain"]
    readonly_fields = [
        "user",
        "code",
        "verified_email",
        "basis_domain",
        "appeal",
        "created_at",
        "updated_at",
    ]
