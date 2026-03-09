"""
WebSocket URL routing for Writer app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/writer/manuscript/(?P<manuscript_id>\d+)/$",
        consumers.WriterConsumer.as_asgi(),
    ),
]
