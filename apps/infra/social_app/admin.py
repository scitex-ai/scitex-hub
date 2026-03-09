from django.contrib import admin
from .models import UserFollow, RepositoryStar, Activity


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    list_filter = ("created_at",)
    search_fields = ("follower__username", "following__username")
    readonly_fields = ("created_at",)


@admin.register(RepositoryStar)
class RepositoryStarAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "starred_at")
    list_filter = ("starred_at",)
    search_fields = ("user__username", "project__name")
    readonly_fields = ("starred_at",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "activity_type",
        "target_user",
        "target_project",
        "created_at",
    )
    list_filter = ("activity_type", "created_at")
    search_fields = ("user__username", "target_user__username", "target_project__name")
    readonly_fields = ("created_at",)
