"""
Channel REST API views.
"""

from django.utils.text import slugify
from rest_framework import generics, permissions

from ..models import Channel, ChannelMembership, Participant
from ..serializers import ChannelSerializer


class ChannelListCreateView(generics.ListCreateAPIView):
    """
    GET  /comms/api/channels/  -- List channels for current user
    POST /comms/api/channels/  -- Create channel
    """

    serializer_class = ChannelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return channels where the current user is a member."""
        user = self.request.user
        try:
            participant = Participant.objects.get(user=user, participant_type="user")
        except Participant.DoesNotExist:
            return Channel.objects.none()

        member_channel_ids = ChannelMembership.objects.filter(
            participant=participant
        ).values_list("channel_id", flat=True)

        return Channel.objects.filter(
            id__in=member_channel_ids, is_archived=False
        ).prefetch_related("memberships")

    def perform_create(self, serializer):
        """Create channel and add creator as owner."""
        user = self.request.user
        participant, _created = Participant.objects.get_or_create(
            user=user,
            participant_type="user",
            defaults={"display_name": user.get_full_name() or user.username},
        )

        name = serializer.validated_data["name"]
        slug = slugify(name)

        # Ensure unique slug
        base_slug = slug
        counter = 1
        while Channel.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        channel = serializer.save(created_by=participant, slug=slug)

        ChannelMembership.objects.create(
            channel=channel, participant=participant, role="owner"
        )


class ChannelDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /comms/api/channels/<slug>/  -- Channel detail
    PATCH /comms/api/channels/<slug>/  -- Update channel
    """

    serializer_class = ChannelSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        return Channel.objects.filter(is_archived=False).prefetch_related("memberships")
