"""Channel-layer push event handlers for TerminalConsumer.

These methods are invoked by Django Channels when a message arrives on a
channel group that this consumer has joined (speech, media, capture).
"""

from __future__ import annotations

import base64
import json
import logging

logger = logging.getLogger(__name__)


class ChannelEventsMixin:
    """Mixin that adds channel-layer event handler methods to a consumer."""

    async def tts_speak(self, event):
        """Forward TTS speech request to browser via WebSocket.

        The browser terminal intercepts messages prefixed with
        ``\\x1b]9999;speak:`` and plays them via ``/llm/api/tts/``.
        """
        text = event.get("text", "")
        if text:
            b64 = base64.b64encode(text.encode()).decode()
            await self.send(text_data=f"\x1b]9999;speak:{b64}\x07")

    async def media_display(self, event):
        """Forward media display request to browser via WebSocket.

        The browser terminal intercepts ``\\x1b]9998;media:`` escapes
        and renders an overlay image/file preview above the terminal.
        """
        media = event.get("media", {})
        if media:
            payload = json.dumps(media)
            b64 = base64.b64encode(payload.encode()).decode()
            await self.send(text_data=f"\x1b]9998;media:{b64}\x07")

    async def capture_request(self, event):
        """Forward capture request to browser via WebSocket.

        The browser terminal intercepts ``\\x1b]9997;`` OSC escapes and
        dispatches them based on the ``action`` field in the payload.
        """
        payload = json.dumps(
            {
                "action": "capture_request",
                "request_id": event["request_id"],
                "project_id": event.get("project_id"),
                "message": event.get("message", ""),
                "needs_permission": event.get("needs_permission", False),
            }
        )
        await self.send(text_data=f"\x1b]9997;{payload}\x07")


# EOF
