"""
Message REST API views.
"""

import hashlib

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.infra.accounts_app.models import APIKey

from ..models import Channel, ChannelMembership, Message, Participant
from ..serializers import AgentSendMessageSerializer, MessageSerializer


class MessageListView(generics.ListAPIView):
    """
    GET /comms/api/channels/<slug>/messages/  -- Paginated message history

    Query params:
        before  -- ISO timestamp cursor for pagination
        limit   -- page size (default 50, max 100)
        search  -- filter by text content
    """

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        slug = self.kwargs["channel_slug"]
        qs = (
            Message.objects.filter(channel__slug=slug, is_deleted=False)
            .select_related("sender")
            .order_by("-created_at")
        )

        # Cursor pagination: messages before a timestamp
        before = self.request.query_params.get("before")
        if before:
            qs = qs.filter(created_at__lt=before)

        # Text search
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(text__icontains=search)

        # Limit
        limit = self.request.query_params.get("limit", 50)
        try:
            limit = min(int(limit), 100)
        except (ValueError, TypeError):
            limit = 50

        return qs[:limit]


class AgentSendMessageView(APIView):
    """
    POST /comms/api/agent/send/  -- Send message as agent (token auth)

    Header: Authorization: Bearer <api_key>
    """

    permission_classes = []  # Custom auth below

    def post(self, request):
        # Authenticate via Bearer token
        participant = self._authenticate_agent(request)
        if participant is None:
            return Response(
                {"detail": "Invalid or missing API token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = AgentSendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        channel_slug = data["channel_slug"]

        # Verify channel and membership
        try:
            channel = Channel.objects.get(slug=channel_slug, is_archived=False)
        except Channel.DoesNotExist:
            return Response(
                {"detail": "Channel not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not ChannelMembership.objects.filter(
            channel=channel, participant=participant
        ).exists():
            return Response(
                {"detail": "Not a member of this channel"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create message
        parent = None
        if data["parent_id"]:
            try:
                parent = Message.objects.get(id=data["parent_id"], channel=channel)
            except Message.DoesNotExist:
                return Response(
                    {"detail": "Parent message not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        message = Message.objects.create(
            channel=channel,
            sender=participant,
            text=data["text"],
            parent=parent,
            attachments=data["attachments"],
            metadata=data["metadata"],
        )

        # Broadcast to WebSocket group
        channel_layer = get_channel_layer()
        if channel_layer:
            group_name = f"comms_channel_{channel_slug}"
            sender_data = {
                "id": participant.id,
                "display_name": participant.display_name,
                "participant_type": participant.participant_type,
            }
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "message.new",
                    "message": {
                        "id": message.id,
                        "channel_id": message.channel_id,
                        "sender": sender_data,
                        "text": message.text,
                        "attachments": message.attachments,
                        "parent_id": message.parent_id,
                        "is_edited": False,
                        "edited_at": None,
                        "metadata": message.metadata,
                        "created_at": message.created_at.isoformat(),
                    },
                },
            )

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _authenticate_agent(request):
        """Resolve Participant from Authorization: Bearer <token> header."""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        key_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            api_key = APIKey.objects.select_related("user").get(
                key_hash=key_hash, is_active=True
            )
        except APIKey.DoesNotExist:
            return None

        try:
            return Participant.objects.get(api_key=api_key, participant_type="agent")
        except Participant.DoesNotExist:
            return None
