"""Legacy session handlers for the terminal broker.

These functions implement the original 1-srun-per-tab spawn pattern.
They receive the broker instance as the first argument.
"""

import logging
import os
import signal
import socket
import threading
import uuid
from pathlib import Path

from ._handler_utils import respawn_pty, send_state
from .session import MAX_RESPAWNS, SessionState, TerminalSession

logger = logging.getLogger(__name__)


def make_exit_callback(broker, client: socket.socket):
    """Create exit callback for session auto-respawn."""

    def on_exit(pty_id):
        with broker.lock:
            session = broker.sessions.get(pty_id)
        if not session or session.state != SessionState.RUNNING:
            return

        session.cleanup_fd()
        session.state = SessionState.EXITED
        send_state(broker, client, pty_id, "exited")

        if session.spawn_count < MAX_RESPAWNS:
            backoff = min(2 ** (session.spawn_count - 1), 4)
            logger.info(
                f"PTY {pty_id[:8]}: scheduling respawn in {backoff}s "
                f"(attempt {session.spawn_count + 1}/{MAX_RESPAWNS})"
            )
            timer = threading.Timer(
                backoff, _respawn_session, args=(broker, pty_id, client)
            )
            timer.daemon = True
            timer.start()
        else:
            session.state = SessionState.DEAD
            send_state(broker, client, pty_id, "dead")
            logger.warning(f"PTY {pty_id[:8]}: max respawns reached, marking DEAD")

    return on_exit


def _respawn_session(broker, pty_id: str, client: socket.socket):
    """Respawn a session after exit."""
    with broker.lock:
        session = broker.sessions.get(pty_id)
    if not session or session.state == SessionState.DEAD:
        return
    respawn_pty(broker, session, client, make_exit_callback)


def handle_spawn_legacy(broker, msg: dict, client: socket.socket) -> dict:
    """Legacy spawn: one srun per tab. Reattaches if session exists."""
    username = msg["username"]
    screen_session = msg.get("screen_session", "scitex-0")
    key = (username, screen_session)

    with broker.lock:
        existing_id = broker.session_index.get(key)
        existing = broker.sessions.get(existing_id) if existing_id else None

        if existing:
            if existing.state == SessionState.RUNNING and existing.fd is not None:
                # Replay scrollback before starting live output
                import base64

                scrollback = existing.get_scrollback()
                if scrollback:
                    broker._send_message(
                        client,
                        {
                            "action": "output",
                            "session_id": existing_id,
                            "data": base64.b64encode(scrollback).decode("ascii"),
                        },
                    )
                existing.client_socket = client
                logger.info(f"PTY {existing_id[:8]}: reattaching client")

                existing.on_exit_callback = make_exit_callback(broker, client)
                existing.start_reader(broker._make_output_callback(client))

                if existing.pid and existing.pid > 0:
                    try:
                        os.kill(existing.pid, signal.SIGWINCH)
                    except ProcessLookupError:
                        pass

                return {"status": "ok", "session_id": existing_id}

            elif existing.state in (SessionState.EXITED, SessionState.DEAD):
                existing.spawn_count = 0
                existing.client_socket = client
                if existing.respawn():
                    existing.on_exit_callback = make_exit_callback(broker, client)
                    existing.start_reader(broker._make_output_callback(client))
                    logger.info(f"PTY {existing_id[:8]}: respawned on reattach")
                    return {"status": "ok", "session_id": existing_id}
                else:
                    broker.sessions.pop(existing_id, None)
                    broker.session_index.pop(key, None)

    # No existing session — spawn new one
    session_id = str(uuid.uuid4())
    try:
        session = TerminalSession(
            session_id=session_id,
            username=username,
            user_data_dir=Path(msg["user_data_dir"]),
            project_dir=Path(msg["project_dir"]),
            container_path=msg["container_path"],
            project_slug=msg["project_slug"],
            screen_session=screen_session,
        )
        session.client_socket = client

        if not session.spawn():
            return {"status": "error", "error": "Failed to spawn PTY"}

        session.on_exit_callback = make_exit_callback(broker, client)
        session.start_reader(broker._make_output_callback(client))

        with broker.lock:
            broker.sessions[session_id] = session
            broker.session_index[key] = session_id

        return {"status": "ok", "session_id": session_id}

    except Exception as e:
        logger.error(f"Spawn error: {e}")
        return {"status": "error", "error": str(e)}


def handle_restart_legacy(broker, msg: dict, client: socket.socket) -> dict:
    """Handle explicit restart request from user."""
    session_id = msg.get("session_id")
    with broker.lock:
        session = broker.sessions.get(session_id)

    if not session:
        return {"status": "error", "error": "Session not found"}

    session.spawn_count = 0
    session.cleanup_fd()
    session.client_socket = client

    if respawn_pty(broker, session, client, make_exit_callback):
        return {"status": "ok", "session_id": session_id}
    return {"status": "error", "error": "Respawn failed"}


# EOF
