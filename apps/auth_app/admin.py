from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, EmailVerification, LoginHistory


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fieldsets = (
        (
            "Profile Information",
            {"fields": ("profession", "research_field", "institution", "bio")},
        ),
        (
            "Verification",
            {"fields": ("is_academic_verified",), "classes": ("collapse",)},
        ),
        (
            "Preferences",
            {
                "fields": ("email_notifications", "weekly_digest"),
                "classes": ("collapse",),
            },
        ),
        (
            "Activity",
            {
                "fields": (
                    "last_login_at",
                    "total_login_count",
                    "profile_completed",
                    "profile_completion_date",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = (
        "is_academic_verified",
        "profile_completed",
        "profile_completion_date",
        "last_login_at",
    )


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("email", "code", "is_verified", "created_at", "expires_at")
    list_filter = ("is_verified", "created_at")
    search_fields = ("email", "user__username")
    readonly_fields = ("created_at", "verified_at")

    def has_change_permission(self, request, obj=None):
        # Make email verifications read-only after creation
        return False


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "timestamp",
        "login_method",
        "success",
        "ip_address",
        "short_user_agent",
    )
    list_filter = ("success", "login_method", "timestamp")
    search_fields = ("user__username", "user__email", "ip_address")
    readonly_fields = (
        "user",
        "timestamp",
        "ip_address",
        "user_agent",
        "login_method",
        "success",
        "failure_reason",
    )
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    def short_user_agent(self, obj):
        """Show truncated user agent"""
        if obj.user_agent:
            return obj.user_agent[:50] + "..." if len(obj.user_agent) > 50 else obj.user_agent
        return "-"
    short_user_agent.short_description = "Device/Browser"

    def has_add_permission(self, request):
        return False  # Logins are logged automatically

    def has_change_permission(self, request, obj=None):
        return False  # Login history should not be editable

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete login history (for GDPR requests)
        return request.user.is_superuser


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
