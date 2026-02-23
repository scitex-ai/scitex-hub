"""Terminal broker server — manages PTY sessions outside Daphne's asyncio loop.

Sessions persist across client disconnects. Reconnecting clients with
the same (username, tmux_session) reattach to the existing PTY fd.
"""

import base64
import json
import logging
import os
import signal
import socket
import struct
import sys
import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

from .session import TerminalSession

logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/scitex-terminal-broker.sock"


class TerminalBroker:
    """Broker server managing PTY sessions outside Daphne's asyncio loop."""

    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
        self.sessions: Dict[str, TerminalSession] = {}
        # Index: (username, tmux_session) → session_id for reattach
        self.session_index: Dict[tuple, str] = {}
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.lock = threading.Lock()
        signal.signal(signal.SIGCHLD, self._sigchld_handler)

    def _sigchld_handler(self, signum, frame):
        """Reap zombie children."""
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                logger.debug(f"Reaped child PID {pid}, status {status}")
            except ChildProcessError:
                break

    def start(self):
        """Start the broker server."""
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        os.chmod(self.socket_path, 0o666)
        self.server_socket.listen(100)
        self.running = True

        logger.info(f"Terminal broker listening on {self.socket_path}")

        while self.running:
            try:
                client, _ = self.server_socket.accept()
                threading.Thread(
                    target=self._handle_client, args=(client,), daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")

    def _handle_client(self, client: socket.socket):
        """Handle a client connection.

        On disconnect, the tmux session persists for future reattach.
        """
        session_id = None
        try:
            while True:
                length_data = client.recv(4)
                if not length_data:
                    break

                msg_length = struct.unpack(">I", length_data)[0]
                if msg_length > 1024 * 1024:
                    break

                data = b""
                while len(data) < msg_length:
                    chunk = client.recv(msg_length - len(data))
                    if not chunk:
                        break
                    data += chunk

                if len(data) < msg_length:
                    break

                msg = json.loads(data.decode("utf-8"))
                response = self._handle_message(msg, client)

                if response:
                    self._send_message(client, response)

                if msg.get("action") == "spawn" and response.get("status") == "ok":
                    session_id = response.get("session_id")

        except Exception as e:
            logger.debug(f"Client handler error: {e}")
        finally:
            # Detach only — tmux session persists for reattach
            if session_id:
                with self.lock:
                    session = self.sessions.get(session_id)
                if session:
                    session.running = False
                    logger.info(f"Session {session_id}: client detached")
            try:
                client.close()
            except:
                pass

    def _send_message(self, sock: socket.socket, msg: dict):
        """Send a length-prefixed JSON message."""
        data = json.dumps(msg).encode("utf-8")
        sock.sendall(struct.pack(">I", len(data)) + data)

    def _handle_message(self, msg: dict, client: socket.socket) -> Optional[dict]:
        """Handle incoming message."""
        action = msg.get("action")

        if action == "spawn":
            return self._handle_spawn(msg, client)
        elif action == "input":
            return self._handle_input(msg)
        elif action == "resize":
            return self._handle_resize(msg)
        elif action == "close":
            return self._handle_close(msg)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    def _handle_spawn(self, msg: dict, client: socket.socket) -> dict:
        """Handle spawn request. Reattaches to existing session if available."""
        username = msg["username"]
        tmux_session = msg.get("tmux_session", "scitex-0")
        key = (username, tmux_session)

        # Check for existing session to reattach
        with self.lock:
            existing_id = self.session_index.get(key)
            existing = self.sessions.get(existing_id) if existing_id else None
            if existing and existing.fd is not None:
                existing.client_socket = client
                existing.running = True
                logger.info(f"Session {existing_id}: reattaching client")

                def reattach_cb(sid, data):
                    try:
                        self._send_message(
                            client,
                            {
                                "action": "output",
                                "session_id": sid,
                                "data": base64.b64encode(data).decode("ascii"),
                            },
                        )
                    except:
                        pass

                existing.start_reader(reattach_cb)

                # Force tmux to redraw screen by sending SIGWINCH
                if existing.pid and existing.pid > 0:
                    try:
                        os.kill(existing.pid, signal.SIGWINCH)
                    except ProcessLookupError:
                        pass

                return {"status": "ok", "session_id": existing_id}

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
                tmux_session=tmux_session,
            )
            session.client_socket = client

            if not session.spawn():
                return {"status": "error", "error": "Failed to spawn PTY"}

            def output_cb(sid, data):
                try:
                    self._send_message(
                        client,
                        {
                            "action": "output",
                            "session_id": sid,
                            "data": base64.b64encode(data).decode("ascii"),
                        },
                    )
                except:
                    pass

            session.start_reader(output_cb)

            with self.lock:
                self.sessions[session_id] = session
                self.session_index[key] = session_id

            return {"status": "ok", "session_id": session_id}

        except Exception as e:
            logger.error(f"Spawn error: {e}")
            return {"status": "error", "error": str(e)}

    def _handle_input(self, msg: dict) -> Optional[dict]:
        """Handle input from client."""
        session_id = msg.get("session_id")
        data = base64.b64decode(msg.get("data", ""))

        with self.lock:
            session = self.sessions.get(session_id)

        if session:
            session.write(data)
        return None

    def _handle_resize(self, msg: dict) -> Optional[dict]:
        """Handle resize request."""
        session_id = msg.get("session_id")
        rows = msg.get("rows", 24)
        cols = msg.get("cols", 80)

        with self.lock:
            session = self.sessions.get(session_id)

        if session:
            session.resize(rows, cols)
        return None

    def _handle_close(self, msg: dict) -> dict:
        """Handle close request."""
        session_id = msg.get("session_id")
        self._close_session(session_id)
        return {"status": "ok"}

    def _close_session(self, session_id: str):
        """Close and remove a session."""
        with self.lock:
            session = self.sessions.pop(session_id, None)
            # Clean up index
            self.session_index = {
                k: v for k, v in self.session_index.items() if v != session_id
            }

        if session:
            session.close()

    def stop(self):
        """Stop the broker."""
        self.running = False

        with self.lock:
            for session in list(self.sessions.values()):
                session.close()
            self.sessions.clear()
            self.session_index.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        logger.info("Terminal broker stopped")


def main():
    """Run the terminal broker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] terminal-broker: %(message)s",
    )

    broker = TerminalBroker()

    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        broker.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        broker.start()
    except KeyboardInterrupt:
        broker.stop()


if __name__ == "__main__":
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    main()


# EOF
