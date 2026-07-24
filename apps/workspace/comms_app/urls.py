"""
Comms app URL configuration.

REST API endpoints:
    /comms/api/channels/                       -- List/create channels
    /comms/api/channels/<slug>/                -- Channel detail/update
    /comms/api/channels/<slug>/messages/       -- Message history
    /comms/api/participants/                   -- List participants visible
                                                  to the caller (read-only;
                                                  membership-scoped)
    /comms/api/agent/send/                     -- Agent send message
"""

from django.urls import path

from apps.infra.workspace_app.views import workspace_shell

from .views import (
    AgentSendMessageView,
    ChannelDetailView,
    ChannelListCreateView,
    MessageListView,
    ParticipantListView,
)

app_name = "comms_app"

urlpatterns = [
    # Comms index — workspace shell with the comms module active (same
    # pattern as discovery_app). Without this, the registry URL
    # /apps/comms/ (launcher "Chat" tile) was a 404: the app only
    # exposed API endpoints (nav-404 batch #3).
    path("", workspace_shell, {"module": "comms"}, name="index"),
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
    # Participant endpoints (read-only: rows are minted server-side only —
    # see ParticipantListView's docstring for why POST was removed).
    path(
        "api/participants/",
        ParticipantListView.as_view(),
        name="participant-list",
    ),
    # Agent endpoints
    path("api/agent/send/", AgentSendMessageView.as_view(), name="agent-send"),
]
