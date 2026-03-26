"""
WebSocket URL routing for Comms app.
"""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/comms/channel/(?P<channel_slug>[\w-]+)/$",
        consumers.CommsConsumer.as_asgi(),
    ),
]
