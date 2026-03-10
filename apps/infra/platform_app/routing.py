"""WebSocket routing for platform_app."""

from django.urls import path

from .consumers.realtime_consumer import PlatformRealtimeConsumer

websocket_urlpatterns = [
    path(
        "ws/platform/realtime/<str:app>/<str:channel>/<str:resource_id>/",
        PlatformRealtimeConsumer.as_asgi(),
    ),
]
