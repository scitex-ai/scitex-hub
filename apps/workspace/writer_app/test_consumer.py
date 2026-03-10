"""Simple test consumer to verify WebSocket works."""

from channels.generic.websocket import AsyncWebsocketConsumer
import json


class TestConsumer(AsyncWebsocketConsumer):
    """Minimal test consumer."""

    async def connect(self):
        """Accept all connections."""
        print(f"[TestConsumer] Connection accepted!")
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {"type": "welcome", "message": "Test WebSocket connected successfully!"}
            )
        )

    async def disconnect(self, close_code):
        """Handle disconnect."""
        print(f"[TestConsumer] Disconnected: {close_code}")

    async def receive(self, text_data):
        """Echo back received messages."""
        print(f"[TestConsumer] Received: {text_data}")
        await self.send(text_data=text_data)
