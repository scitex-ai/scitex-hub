"""
Participant REST API views.
"""

from django.db.models import Q
from rest_framework import generics, permissions

from ..models import ChannelMembership, Participant
from ..serializers import ParticipantSerializer


class ParticipantListView(generics.ListAPIView):
    """
    GET /comms/api/participants/  -- List participants VISIBLE to the caller.

    Tenant isolation (operator mandate #1: no cross-user data leakage).
    ------------------------------------------------------------------
    This endpoint used to be a ``ListCreateAPIView`` with a class-level
    ``queryset = Participant.objects.all()``. That is a cross-tenant leak:
    ``ParticipantSerializer`` exposes ``display_name`` (populated from
    ``User.get_full_name()`` in ``ChannelListCreateView.perform_create``),
    ``agent_name``, ``avatar_url``, ``is_online`` and ``last_seen``, so ANY
    authenticated caller could enumerate every tenant's real names, agent
    fleet and presence data. The hub auto-logs browsers in as pooled
    anonymous visitors (``apps/infra/project_app/middleware.py``), whose skip
    list does not cover ``/apps/comms/api/participants/`` — so the leak was
    reachable without registering.

    The only relation that legitimately links one Participant to another is
    ``ChannelMembership``. Membership is the authoritative access rule
    everywhere else in this app (``ChannelListCreateView.get_queryset``,
    ``MessageListView``, ``AgentSendMessageView``, ``CommsConsumer.connect``),
    so the visible set is: the caller's OWN Participant row, plus Participants
    who co-member a non-archived channel the caller belongs to.

    ``Channel.project`` is deliberately NOT used for scoping: it is nullable
    and no code path in this app authorizes off it.

    POST is gone on purpose. Every Participant row is minted server-side
    (``ChannelListCreateView.perform_create``, ``orochi_bridge`` management
    command, Django admin). The serializer cannot set ``user`` or ``api_key``,
    so a client-created row could never authenticate — it was pure
    identity-spoofing surface: an ``agent_name="orochi-bridge"`` row makes the
    bridge's ``Participant.objects.get(...)`` raise ``MultipleObjectsReturned``
    on every poll (remote DoS), and there is no throttle on write.
    """

    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return the caller's own Participant plus their channel co-members.

        Fails CLOSED: a user with no Participant row (the common case — rows
        are only minted on first channel creation) gets an EMPTY list, never
        an exception and never the whole table. Only ``DoesNotExist`` is
        caught; any other error propagates rather than degrading into a
        silent, unscoped fallback.
        """
        try:
            me = Participant.objects.get(
                user=self.request.user, participant_type="user"
            )
        except Participant.DoesNotExist:
            return Participant.objects.none()

        my_channel_ids = ChannelMembership.objects.filter(
            participant=me, channel__is_archived=False
        ).values_list("channel_id", flat=True)

        # `Q(pk=me.pk)` is required as its own term: a caller with zero
        # memberships must still see themselves. `.distinct()` is required
        # because the reverse join returns a co-member once per shared
        # channel (`unique_together` is (channel, participant), not
        # participant). The reverse accessor is `channel_memberships`
        # (ChannelMembership.participant.related_name) — `memberships` is
        # Channel's and would raise FieldError at request time.
        return (
            Participant.objects.filter(
                Q(pk=me.pk)
                | Q(channel_memberships__channel_id__in=my_channel_ids)
            )
            .distinct()
            .order_by("id")
        )
