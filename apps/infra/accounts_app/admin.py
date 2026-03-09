from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "institution",
        "is_academic_ja",
        "profile_visibility",
        "created_at",
    )
    list_filter = ("is_academic_ja", "profile_visibility", "is_public", "created_at")
    search_fields = ("user__username", "user__email", "institution", "bio")
    readonly_fields = ("created_at", "updated_at", "is_academic_ja")

    fieldsets = (
        ("User", {"fields": ("user",)}),
        (
            "Profile Information",
            {
                "fields": (
                    "avatar",
                    "bio",
                    "location",
                    "institution",
                    "research_interests",
                )
            },
        ),
        (
            "Academic Information",
            {"fields": ("orcid", "academic_title", "department", "is_academic_ja")},
        ),
        (
            "Professional Links",
            {
                "fields": (
                    "website",
                    "google_scholar",
                    "linkedin",
                    "researchgate",
                    "twitter",
                )
            },
        ),
        (
            "Privacy Settings",
            {
                "fields": (
                    "profile_visibility",
                    "is_public",
                    "show_email",
                    "allow_collaboration",
                    "allow_messages",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "last_active_repository",
                    "deletion_scheduled_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
