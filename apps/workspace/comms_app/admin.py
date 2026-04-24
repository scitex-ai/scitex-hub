from django.contrib import admin

from .models import Channel, ChannelMembership, Message, Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "participant_type",
        "is_online",
        "last_seen",
        "created_at",
    ]
    list_filter = ["participant_type", "is_online"]
    search_fields = ["display_name", "agent_name", "user__username"]
    readonly_fields = ["created_at"]


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "channel_type", "project", "is_archived", "created_at"]
    list_filter = ["channel_type", "is_archived"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ChannelMembership)
class ChannelMembershipAdmin(admin.ModelAdmin):
    list_display = ["participant", "channel", "role", "joined_at", "is_muted"]
    list_filter = ["role", "is_muted"]
    search_fields = ["participant__display_name", "channel__name"]
    readonly_fields = ["joined_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "sender",
        "channel",
        "short_text",
        "is_edited",
        "is_deleted",
        "created_at",
    ]
    list_filter = ["is_edited", "is_deleted", "created_at"]
    search_fields = ["text", "sender__display_name", "channel__name"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["sender", "channel", "parent"]

    @admin.display(description="Text")
    def short_text(self, obj):
        return obj.text[:80] + "..." if len(obj.text) > 80 else obj.text
