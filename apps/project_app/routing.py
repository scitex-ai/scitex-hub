#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket URL routing for Project app.
"""

from django.urls import re_path
from . import websocket_consumers

websocket_urlpatterns = [
    # Port proxy WebSocket: /{username}/{project}/ws/?port={port}
    re_path(
        r"^(?P<username>[\w-]+)/(?P<slug>[\w-]+)/ws/$",
        websocket_consumers.PortProxyWebSocketConsumer.as_asgi(),
    ),
]

# EOF
