"""Terminal broker server — manages PTY sessions outside Daphne's asyncio loop.

Sessions persist across client disconnects. Reconnecting clients with
the same (username, session_name) reattach to the existing PTY fd.

Supports two modes (controlled by SCITEX_CLOUD_SLURM_SHARED_ALLOCATION env var):
- Legacy: one srun per terminal tab
- Shared: one sbatch per (user, project), shells via srun --overlap
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
from typing import Dict, Optional

from .session import TerminalSession

logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/scitex-terminal-broker.sock"

# Feature flag: when True, use shared sbatch allocation per (user, project)
SHARED_ALLOCATION = (
    os.environ.get("SCITEX_CLOUD_SLURM_SHARED_ALLOCATION", "")
    or os.environ.get("SCITEX_SHARED_ALLOCATION", "")  # backward compat
).lower() in ("true", "1", "yes")


class TerminalBroker:
    """Broker server managing PTY sessions outside Daphne's asyncio loop."""

    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
        # Legacy mode: 1 srun per tab
        self.sessions: Dict[str, TerminalSession] = {}
        self.session_index: Dict[tuple, str] = {}  # (username, screen_session) -> id
        # Shared allocation mode: 1 sbatch per (user, project), N shells inside
        self.allocations: Dict[str, object] = {}  # alloc_id -> Allocation
        self.alloc_index: Dict[tuple, str] = {}  # (username, project_slug) -> alloc_id
        self.shells: Dict[str, object] = {}  # shell_id -> Shell
        self.shell_index: Dict[tuple, str] = (
            {}
        )  # (username, screen_session) -> shell_id
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.lock = threading.Lock()
        self._monitor = None
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

        if SHARED_ALLOCATION:
            from .allocation_monitor import AllocationMonitor

            self._monitor = AllocationMonitor(self)
            self._monitor.start()

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
        """Handle a client connection."""
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
            logger.error(f"Client handler error: {e}", exc_info=True)
            try:
                self._send_message(
                    client,
                    {"status": "error", "error": str(e)},
                )
            except Exception:
                pass
        finally:
            if session_id:
                logger.info(f"Session {session_id}: client detached")
            try:
                client.close()
            except Exception:
                pass

    def _send_message(self, sock: socket.socket, msg: dict):
        """Send a length-prefixed JSON message."""
        data = json.dumps(msg).encode("utf-8")
        sock.sendall(struct.pack(">I", len(data)) + data)

    def _handle_message(self, msg: dict, client: socket.socket) -> Optional[dict]:
        """Route incoming message to the appropriate handler."""
        action = msg.get("action")

        if action == "spawn":
            return self._handle_spawn(msg, client)
        elif action == "input":
            return self._handle_input(msg)
        elif action == "resize":
            return self._handle_resize(msg)
        elif action == "close":
            return self._handle_close(msg)
        elif action == "restart":
            return self._handle_restart(msg, client)
        elif action == "stop_allocation":
            return self._handle_stop_allocation(msg)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    def _make_output_callback(self, client: socket.socket):
        """Create an output callback that sends PTY data to the client."""

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
            except Exception:
                pass

        return output_cb

    # ------------------------------------------------------------------
    # Spawn / Restart — dispatched to legacy or shared handler modules
    # ------------------------------------------------------------------

    def _handle_spawn(self, msg: dict, client: socket.socket) -> dict:
        """Dispatch spawn to shared or legacy mode."""
        if SHARED_ALLOCATION:
            from ._handlers_shared import handle_spawn_shared

            return handle_spawn_shared(self, msg, client)

        from ._handlers_legacy import handle_spawn_legacy

        return handle_spawn_legacy(self, msg, client)

    def _handle_restart(self, msg: dict, client: socket.socket) -> dict:
        """Dispatch restart to shared or legacy handler."""
        if SHARED_ALLOCATION:
            from ._handlers_shared import handle_restart_shared

            return handle_restart_shared(self, msg, client)

        from ._handlers_legacy import handle_restart_legacy

        return handle_restart_legacy(self, msg, client)

    def _handle_stop_allocation(self, msg: dict) -> dict:
        """Stop a shared allocation and all its shells."""
        from ._handlers_shared import handle_stop_allocation

        return handle_stop_allocation(self, msg)

    # ------------------------------------------------------------------
    # Input / Resize / Close — work with both sessions and shells
    # ------------------------------------------------------------------

    def _handle_input(self, msg: dict) -> Optional[dict]:
        """Handle input from client."""
        session_id = msg.get("session_id")
        data = base64.b64decode(msg.get("data", ""))

        with self.lock:
            target = self.sessions.get(session_id) or self.shells.get(session_id)

        if target:
            target.write(data)
        return None

    def _handle_resize(self, msg: dict) -> Optional[dict]:
        """Handle resize request."""
        session_id = msg.get("session_id")
        rows = msg.get("rows", 24)
        cols = msg.get("cols", 80)

        with self.lock:
            target = self.sessions.get(session_id) or self.shells.get(session_id)

        if target:
            target.resize(rows, cols)
        return None

    def _handle_close(self, msg: dict) -> dict:
        """Handle close request."""
        session_id = msg.get("session_id")
        # Check shells first (shared mode), then legacy sessions
        with self.lock:
            shell = self.shells.pop(session_id, None)
            alloc = None
            if shell:
                self.shell_index = {
                    k: v for k, v in self.shell_index.items() if v != session_id
                }
                alloc = self.allocations.get(shell.allocation_id)
        if shell:
            shell.close()
            if alloc:
                alloc.decrement_shells()
            return {"status": "ok"}

        # Legacy session close
        with self.lock:
            session = self.sessions.pop(session_id, None)
            self.session_index = {
                k: v for k, v in self.session_index.items() if v != session_id
            }
        if session:
            session.close()
        return {"status": "ok"}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self):
        """Stop the broker and clean up all sessions/allocations."""
        self.running = False

        if self._monitor:
            self._monitor.stop()
            self._monitor = None

        with self.lock:
            for session in list(self.sessions.values()):
                session.close()
            self.sessions.clear()
            self.session_index.clear()

        # Clean up shared allocations
        from ._handlers_shared import stop_all_allocations

        stop_all_allocations(self)

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
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
