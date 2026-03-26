"""
Comms app URL configuration.

REST API endpoints:
    /comms/api/channels/                       -- List/create channels
    /comms/api/channels/<slug>/                -- Channel detail/update
    /comms/api/channels/<slug>/messages/       -- Message history
    /comms/api/participants/                   -- List/create participants
    /comms/api/agent/send/                     -- Agent send message
"""

from django.urls import path

from .views import (
    AgentSendMessageView,
    ChannelDetailView,
    ChannelListCreateView,
    MessageListView,
    ParticipantListCreateView,
)

app_name = "comms_app"

urlpatterns = [
    # Channel endpoints
    path("api/channels/", ChannelListCreateView.as_view(), name="channel-list-create"),
    path(
        "api/channels/<slug:slug>/",
        ChannelDetailView.as_view(),
        name="channel-detail",
    ),
    # Message endpoints
    path(
        "api/channels/<slug:channel_slug>/messages/",
        MessageListView.as_view(),
        name="message-list",
    ),
    # Participant endpoints
    path(
        "api/participants/",
        ParticipantListCreateView.as_view(),
        name="participant-list-create",
    ),
    # Agent endpoints
    path("api/agent/send/", AgentSendMessageView.as_view(), name="agent-send"),
]
