"""
DRF Serializers for Comms app.
"""

from rest_framework import serializers

from .models import Channel, ChannelMembership, Message, Participant


class ParticipantSerializer(serializers.ModelSerializer):
    """Serializer for Participant model."""

    class Meta:
        model = Participant
        fields = [
            "id",
            "participant_type",
            "display_name",
            "agent_name",
            "avatar_url",
            "is_online",
            "last_seen",
            "created_at",
        ]
        read_only_fields = ["id", "is_online", "last_seen", "created_at"]


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for Channel model."""

    created_by = ParticipantSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "channel_type",
            "project",
            "created_by",
            "is_archived",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_by",
            "is_archived",
            "created_at",
            "updated_at",
        ]

    def get_member_count(self, obj):
        return obj.memberships.count()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    sender = ParticipantSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "channel",
            "sender",
            "text",
            "attachments",
            "parent",
            "is_edited",
            "edited_at",
            "is_deleted",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "is_edited",
            "edited_at",
            "is_deleted",
            "created_at",
        ]


class ChannelMembershipSerializer(serializers.ModelSerializer):
    """Serializer for ChannelMembership model."""

    participant = ParticipantSerializer(read_only=True)

    class Meta:
        model = ChannelMembership
        fields = [
            "id",
            "channel",
            "participant",
            "role",
            "joined_at",
            "is_muted",
            "last_read_at",
        ]
        read_only_fields = ["id", "joined_at", "last_read_at"]


class AgentSendMessageSerializer(serializers.Serializer):
    """Serializer for agent message send endpoint."""

    channel_slug = serializers.SlugField()
    text = serializers.CharField()
    parent_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    attachments = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
    metadata = serializers.DictField(required=False, default=dict)
