"""
Admin configuration for collaboration models.

Manages real-time collaboration sessions and user presence.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from ..models import WriterPresence, CollaborativeSession


@admin.register(WriterPresence)
class WriterPresenceAdmin(admin.ModelAdmin):
    """Admin interface for WriterPresence model."""

    list_display = [
        "user_display",
        "manuscript_display",
        "is_online_badge",
        "current_section",
        "last_seen",
    ]
    list_filter = [
        "is_active",
        "last_seen",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "manuscript__title",
        "current_section",
    ]
    readonly_fields = [
        "id",
        "last_seen",
    ]
    fieldsets = (
        (
            "Presence Information",
            {"fields": ("user", "manuscript", "current_section", "cursor_position")},
        ),
        ("Status", {"fields": ("is_active", "last_seen")}),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )
    date_hierarchy = "last_seen"
    ordering = ["-last_seen"]

    def user_display(self, obj):
        """Display user information."""
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return "-"

    user_display.short_description = "User"

    def manuscript_display(self, obj):
        """Display manuscript title."""
        if obj.manuscript:
            title = obj.manuscript.title
            return title[:40] + "..." if len(title) > 40 else title
        return "-"

    manuscript_display.short_description = "Manuscript"

    def is_online_badge(self, obj):
        """Display online status badge."""
        # Consider online if seen in last 5 minutes and active
        threshold = timezone.now() - timedelta(minutes=5)
        is_online = obj.is_active and obj.last_seen > threshold

        if is_online:
            return format_html(
                '<span style="display: inline-block; width: 10px; height: 10px; '
                'background-color: green; border-radius: 50%; margin-right: 5px;"></span>'
                '<span style="color: green;">Online</span>'
            )
        return format_html(
            '<span style="display: inline-block; width: 10px; height: 10px; '
            'background-color: gray; border-radius: 50%; margin-right: 5px;"></span>'
            '<span style="color: gray;">Offline</span>'
        )

    is_online_badge.short_description = "Status"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("user", "manuscript")


@admin.register(CollaborativeSession)
class CollaborativeSessionAdmin(admin.ModelAdmin):
    """Admin interface for CollaborativeSession model."""

    list_display = [
        "session_id_short",
        "manuscript_display",
        "active_users_count",
        "is_active_badge",
        "started_at",
        "ended_at",
    ]
    list_filter = [
        "is_active",
        "started_at",
        "ended_at",
    ]
    search_fields = [
        "session_id",
        "manuscript__title",
        "user__username",
    ]
    readonly_fields = [
        "id",
        "session_id",
        "started_at",
        "ended_at",
    ]
    fieldsets = (
        (
            "Session Information",
            {"fields": ("session_id", "manuscript", "user", "is_active")},
        ),
        ("Locking", {"fields": ("locked_sections",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("started_at", "ended_at"), "classes": ("collapse",)},
        ),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )
    date_hierarchy = "started_at"
    ordering = ["-started_at"]

    def session_id_short(self, obj):
        """Display shortened session ID."""
        if obj.session_id:
            return format_html(
                '<code style="background: #f5f5f5; padding: 2px 5px;">{}</code>',
                str(obj.session_id)[:8],
            )
        return "-"

    session_id_short.short_description = "Session ID"

    def manuscript_display(self, obj):
        """Display manuscript title."""
        if obj.manuscript:
            title = obj.manuscript.title
            return title[:40] + "..." if len(title) > 40 else title
        return "-"

    manuscript_display.short_description = "Manuscript"

    def active_users_count(self, obj):
        """Display user for this session."""
        if obj.user:
            return f"{obj.user.username}"
        return "-"

    active_users_count.short_description = "User"

    def is_active_badge(self, obj):
        """Display active status badge."""
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; '
                'padding: 3px 10px; border-radius: 3px;">ACTIVE</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; '
            'padding: 3px 10px; border-radius: 3px;">ENDED</span>'
        )

    is_active_badge.short_description = "Status"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("manuscript", "user")
