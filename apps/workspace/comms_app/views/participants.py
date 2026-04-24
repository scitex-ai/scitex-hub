"""
Participant REST API views.
"""

from rest_framework import generics, permissions

from ..models import Participant
from ..serializers import ParticipantSerializer


class ParticipantListCreateView(generics.ListCreateAPIView):
    """
    GET  /comms/api/participants/  -- List participants
    POST /comms/api/participants/  -- Create participant
    """

    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Participant.objects.all()
