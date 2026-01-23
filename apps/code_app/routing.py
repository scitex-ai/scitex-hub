"""
WebSocket routing for Code Workspace
"""

from django.urls import path
from .views import terminal

websocket_urlpatterns = [
    path('ws/code/terminal/', terminal.TerminalConsumer.as_asgi()),
]
