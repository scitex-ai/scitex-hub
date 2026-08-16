#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket URL routing for Project app.
"""

from django.urls import path

from .consumers import RepoMonitorConsumer

# NOTE: the `<username>/<slug>/ws/?port=` route and its PortProxyWebSocketConsumer
# were removed as a dead-code SSRF sibling of CodeQL py/partial-ssrf #9385. It
# forwarded to ws://127.0.0.1:<port> for any port in 10000-20000, gated only by a
# range check and `is_public` (so any authenticated tenant could reach another
# tenant's localhost Jupyter/TensorBoard). Nothing in the product built a
# `/ws/?port=` link -- workspace notebooks go through console_app's own API.
# See views/projects/detail.py for the HTTP twin's removal note.
websocket_urlpatterns = [
    # Real-time repository file-change feed
    path("ws/project/repo-monitor/", RepoMonitorConsumer.as_asgi()),
]

# EOF
