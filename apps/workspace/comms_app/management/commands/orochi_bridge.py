"""
orochi_bridge -- Sync Orochi messages into comms_app channels.

Phase 1: Read-only bridge (Orochi -> comms_app).
Polls Orochi REST API and creates Message records in comms_app,
so Orochi agent conversations appear in the scitex.ai workspace.

Usage:
    python manage.py orochi_bridge                # One-shot sync
    python manage.py orochi_bridge --daemon       # Continuous polling
    python manage.py orochi_bridge --interval 10  # Poll every 10s
    python manage.py orochi_bridge --setup        # Initialize channels + participant
"""

import json
import logging
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand

from apps.workspace.comms_app.models import (
    Channel,
    ChannelMembership,
    Message,
    Participant,
)

logger = logging.getLogger("orochi_bridge")

OROCHI_API_BASE = "http://scitex-orochi:8559"
BRIDGE_AGENT_NAME = "orochi-bridge"
BRIDGE_DISPLAY_NAME = "Orochi Bridge"

# Orochi channels to mirror (orochi name -> comms_app slug)
CHANNEL_MAP = {
    "#general": "orochi-general",
    "#deploy": "orochi-deploy",
    "#gitea": "orochi-gitea",
    "#monitoring": "orochi-monitoring",
}


class Command(BaseCommand):
    help = "Sync Orochi messages into comms_app channels"

    def add_arguments(self, parser):
        parser.add_argument(
            "--setup",
            action="store_true",
            help="Initialize bridge participant and channels",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Run continuously with polling",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Poll interval in seconds (default: 5)",
        )

    def handle(self, *args, **options):
        if options["setup"]:
            self._setup()
            return

        bridge = OrochiCommsBridge()

        if options["daemon"]:
            interval = options["interval"]
            self.stdout.write(f"Starting Orochi bridge daemon (interval={interval}s)")
            bridge.run_daemon(interval)
        else:
            count = bridge.sync_once()
            self.stdout.write(f"Synced {count} messages")

    def _setup(self):
        """Create bridge participant and mirror channels."""
        participant, created = Participant.objects.get_or_create(
            agent_name=BRIDGE_AGENT_NAME,
            participant_type="agent",
            defaults={
                "display_name": BRIDGE_DISPLAY_NAME,
            },
        )
        if created:
            self.stdout.write(f"Created participant: {participant}")
        else:
            self.stdout.write(f"Participant exists: {participant}")

        for orochi_ch, comms_slug in CHANNEL_MAP.items():
            channel, created = Channel.objects.get_or_create(
                slug=comms_slug,
                defaults={
                    "name": f"Orochi {orochi_ch}",
                    "channel_type": "public",
                    "description": f"Mirror of Orochi channel {orochi_ch}",
                    "created_by": participant,
                },
            )
            if created:
                self.stdout.write(f"Created channel: {channel}")
            else:
                self.stdout.write(f"Channel exists: {channel}")

            # Ensure bridge is a member
            ChannelMembership.objects.get_or_create(
                channel=channel,
                participant=participant,
                defaults={"role": "admin"},
            )

        self.stdout.write(self.style.SUCCESS("Bridge setup complete"))


class OrochiCommsBridge:
    """Polls Orochi REST API and inserts messages into comms_app."""

    def __init__(self):
        self.bridge_participant = None
        self._last_synced = {}  # channel -> last message timestamp

    def _get_participant(self) -> Participant:
        if self.bridge_participant is None:
            self.bridge_participant = Participant.objects.get(
                agent_name=BRIDGE_AGENT_NAME,
                participant_type="agent",
            )
        return self.bridge_participant

    def _get_or_create_sender(self, sender_name: str) -> Participant:
        """Get or create a Participant for an Orochi agent sender."""
        participant, created = Participant.objects.get_or_create(
            agent_name=sender_name,
            participant_type="agent",
            defaults={
                "display_name": sender_name,
            },
        )
        if created:
            # Add to all mirror channels
            for comms_slug in CHANNEL_MAP.values():
                try:
                    channel = Channel.objects.get(slug=comms_slug)
                    ChannelMembership.objects.get_or_create(
                        channel=channel,
                        participant=participant,
                    )
                except Channel.DoesNotExist:
                    pass
        return participant

    def _fetch_orochi_history(
        self, channel: str, since: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Fetch message history from Orochi REST API."""
        ch_name = channel.lstrip("#")
        url = f"{OROCHI_API_BASE}/api/history/{ch_name}?limit={limit}"
        if since:
            url += f"&since={since}"

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.warning("Failed to fetch Orochi history for %s: %s", channel, exc)
            return []

    def _message_exists(self, orochi_id: str) -> bool:
        """Check if an Orochi message was already synced (by metadata)."""
        return Message.objects.filter(metadata__orochi_id=orochi_id).exists()

    def sync_channel(self, orochi_channel: str, comms_slug: str) -> int:
        """Sync one Orochi channel into the comms_app mirror channel."""
        try:
            channel = Channel.objects.get(slug=comms_slug)
        except Channel.DoesNotExist:
            logger.warning("Comms channel %s not found, run --setup first", comms_slug)
            return 0

        since = self._last_synced.get(orochi_channel)
        messages = self._fetch_orochi_history(orochi_channel, since=since)

        if not messages:
            return 0

        count = 0
        for msg_data in messages:
            # Orochi API returns 'msg_id', not 'id'
            orochi_id = msg_data.get("msg_id", "") or msg_data.get("id", "")
            if not orochi_id:
                continue

            # Skip if already synced
            if self._message_exists(orochi_id):
                continue

            sender_name = msg_data.get("sender", "unknown")

            # Orochi API returns 'content' at top level, not nested in 'payload'
            content = msg_data.get("content", "")
            if not content:
                payload = msg_data.get("payload", {})
                if isinstance(payload, dict):
                    content = payload.get("content", "")
                elif isinstance(payload, str):
                    content = payload

            if not content:
                continue

            # Get or create sender participant
            sender = self._get_or_create_sender(sender_name)

            ts = msg_data.get("ts")

            Message.objects.create(
                channel=channel,
                sender=sender,
                text=content,
                metadata={
                    "orochi_id": orochi_id,
                    "orochi_channel": orochi_channel,
                    "orochi_sender": sender_name,
                    "orochi_ts": ts,
                    "source": "orochi-bridge",
                },
            )
            count += 1

            # Track latest timestamp for incremental sync
            if ts:
                prev = self._last_synced.get(orochi_channel)
                if prev is None or ts > prev:
                    self._last_synced[orochi_channel] = ts

        return count

    def sync_once(self) -> int:
        """Sync all configured channels once."""
        total = 0
        for orochi_ch, comms_slug in CHANNEL_MAP.items():
            count = self.sync_channel(orochi_ch, comms_slug)
            if count > 0:
                logger.info("Synced %d messages from %s", count, orochi_ch)
            total += count
        return total

    def run_daemon(self, interval: int = 5):
        """Continuously poll Orochi and sync messages."""
        logger.info(
            "Orochi bridge daemon started (interval=%ds, channels=%s)",
            interval,
            list(CHANNEL_MAP.keys()),
        )
        while True:
            try:
                self.sync_once()
            except Exception:
                logger.exception("Error in sync cycle")
            time.sleep(interval)
