"""Shared utilities for broker handler modules."""

import logging
import socket

from .session import SessionState

logger = logging.getLogger(__name__)


def send_state(broker, client: socket.socket, pty_id: str, state: str, extra=None):
    """Send a session_state control message to the client."""
    msg = {"action": "session_state", "state": state, "session_id": pty_id}
    if extra:
        msg.update(extra)
    try:
        broker._send_message(client, msg)
    except Exception:
        pass


def respawn_pty(broker, target, client: socket.socket, make_exit_cb, on_fail=None):
    """Common respawn logic for both legacy sessions and shared shells.

    Args:
        target: BasePTY subclass instance (TerminalSession or Shell)
        make_exit_cb: callable(broker, client) -> exit callback
        on_fail: optional callable invoked when respawn fails
    """
    target.state = SessionState.RESPAWNING
    send_state(broker, client, target.pty_id, "respawning")

    if target.respawn():
        target.on_exit_callback = make_exit_cb(broker, client)
        target.start_reader(broker._make_output_callback(client))
        send_state(broker, client, target.pty_id, "running")
        logger.info(f"PTY {target.pty_id[:8]}: respawned successfully")
        return True

    target.state = SessionState.DEAD
    send_state(broker, client, target.pty_id, "dead")
    if on_fail:
        on_fail()
    logger.error(f"PTY {target.pty_id[:8]}: respawn failed")
    return False


# EOF
