"""
Orochi bridge signal — forwards workspace messages to Orochi channels.

Phase 2 of #66: Bidirectional bridge.
When a user sends a message in an orochi-* channel via the workspace UI,
this signal forwards it to the corresponding Orochi channel via REST API.
"""

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.workspace.comms_app.models import Message

logger = logging.getLogger("orochi_bridge")

OROCHI_API_BASE = "http://scitex-orochi:8559"

# Reverse map: comms_app slug -> Orochi channel name
SLUG_TO_OROCHI = {
    "orochi-general": "#general",
    "orochi-deploy": "#deploy",
    "orochi-gitea": "#gitea",
    "orochi-monitoring": "#monitoring",
}


@receiver(post_save, sender=Message)
def forward_to_orochi(sender, instance, created, **kwargs):
    """Forward new workspace messages in orochi-* channels to Orochi."""
    if not created:
        return

    # Only forward messages in orochi-mirror channels
    channel_slug = instance.channel.slug
    orochi_channel = SLUG_TO_OROCHI.get(channel_slug)
    if not orochi_channel:
        return

    # Skip messages that came FROM Orochi (prevent infinite loop)
    metadata = instance.metadata or {}
    if metadata.get("source") == "orochi-bridge":
        return

    # Build sender name
    sender_name = "workspace-user"
    if instance.sender:
        sender_name = (
            instance.sender.display_name
            or instance.sender.agent_name
            or "workspace-user"
        )

    # Forward to Orochi via REST API
    payload = {
        "sender": sender_name,
        "payload": {
            "channel": orochi_channel,
            "content": instance.text,
            "metadata": {
                "source": "scitex-workspace",
                "comms_message_id": instance.id,
                "comms_channel": channel_slug,
            },
        },
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            f"{OROCHI_API_BASE}/api/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            logger.info(
                "Forwarded message to Orochi %s: %s",
                orochi_channel,
                result.get("id", "unknown"),
            )
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning(
            "Failed to forward message to Orochi %s: %s",
            orochi_channel,
            exc,
        )
