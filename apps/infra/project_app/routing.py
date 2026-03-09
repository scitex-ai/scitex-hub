#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket URL routing for Project app.
"""

from django.urls import path, re_path

from . import websocket_consumers
from .consumers import RepoMonitorConsumer

websocket_urlpatterns = [
    # Real-time repository file-change feed
    path("ws/project/repo-monitor/", RepoMonitorConsumer.as_asgi()),
    # Port proxy WebSocket: /{username}/{project}/ws/?port={port}
    re_path(
        r"^(?P<username>[\w-]+)/(?P<slug>[\w-]+)/ws/$",
        websocket_consumers.PortProxyWebSocketConsumer.as_asgi(),
    ),
]

# EOF
