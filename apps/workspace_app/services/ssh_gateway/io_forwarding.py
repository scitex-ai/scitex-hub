"""I/O forwarding between SSH channel and Terminal Broker."""

import base64
import logging
import threading

import paramiko

from .broker_client import SyncBrokerClient

logger = logging.getLogger(__name__)


def forward_io_broker(channel: paramiko.Channel, broker_client: SyncBrokerClient):
    """Forward I/O bidirectionally between SSH channel and broker session."""
    stop_event = threading.Event()

    def channel_to_broker():
        try:
            while not stop_event.is_set():
                data = channel.recv(4096)
                if not data:
                    break
                broker_client.send_input(data)
        except Exception as e:
            logger.debug(f"Channel->broker ended: {e}")
        finally:
            stop_event.set()

    def broker_to_channel():
        try:
            while not stop_event.is_set():
                msg = broker_client.recv_message()
                if not msg:
                    break
                if msg.get("action") == "output":
                    raw = base64.b64decode(msg["data"])
                    channel.sendall(raw)
                elif msg.get("action") == "state":
                    state = msg.get("state")
                    if state in ("exited", "dead"):
                        channel.send(b"\r\nSession ended.\r\n")
                        break
        except Exception as e:
            logger.debug(f"Broker->channel ended: {e}")
        finally:
            stop_event.set()

    t1 = threading.Thread(target=channel_to_broker, daemon=True)
    t2 = threading.Thread(target=broker_to_channel, daemon=True)
    t1.start()
    t2.start()

    stop_event.wait()
    t1.join(timeout=2)
    t2.join(timeout=2)


# EOF
