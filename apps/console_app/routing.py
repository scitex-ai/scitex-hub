"""
WebSocket routing for Console Workspace
"""

from django.urls import path
from .views import terminal

websocket_urlpatterns = [
    path("ws/console/terminal/", terminal.TerminalConsumer.as_asgi()),
]
