"""WebSocket routing for LLM app."""

from django.urls import path

from .consumers import EvalJSConsumer

websocket_urlpatterns = [
    path("ws/llm/eval-js/", EvalJSConsumer.as_asgi()),
]
