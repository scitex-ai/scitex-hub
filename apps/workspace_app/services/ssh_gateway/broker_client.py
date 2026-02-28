"""Synchronous Terminal Broker client for SSH gateway.

Communicates with the Terminal Broker via length-prefixed JSON over Unix socket.
"""

import base64
import json
import logging
import socket
import struct
import threading

logger = logging.getLogger(__name__)

BROKER_SOCKET_PATH = "/tmp/scitex-terminal-broker.sock"


class SyncBrokerClient:
    """Synchronous client for the Terminal Broker Unix socket protocol."""

    def __init__(self, socket_path: str = BROKER_SOCKET_PATH):
        self.socket_path = socket_path
        self.sock = None
        self.session_id = None
        self._lock = threading.Lock()

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

    def _send_message(self, msg: dict):
        data = json.dumps(msg).encode("utf-8")
        with self._lock:
            self.sock.sendall(struct.pack(">I", len(data)) + data)

    def recv_message(self) -> dict | None:
        """Read one length-prefixed JSON message from the broker."""
        length_data = self.sock.recv(4)
        if not length_data or len(length_data) < 4:
            return None
        msg_length = struct.unpack(">I", length_data)[0]
        if msg_length > 1024 * 1024:
            return None
        data = b""
        while len(data) < msg_length:
            chunk = self.sock.recv(msg_length - len(data))
            if not chunk:
                return None
            data += chunk
        return json.loads(data.decode("utf-8"))

    def spawn(
        self,
        username: str,
        user_data_dir: str,
        project_dir: str,
        container_path: str,
        project_slug: str,
        screen_session: str = "ssh-0",
    ) -> dict:
        self._send_message(
            {
                "action": "spawn",
                "username": username,
                "user_data_dir": str(user_data_dir),
                "project_dir": str(project_dir),
                "container_path": container_path,
                "project_slug": project_slug,
                "screen_session": screen_session,
            }
        )
        resp = self.recv_message()
        if resp and resp.get("status") == "ok":
            self.session_id = resp.get("session_id")
        return resp or {"status": "error", "error": "No response from broker"}

    def send_input(self, data: bytes):
        self._send_message(
            {
                "action": "input",
                "session_id": self.session_id,
                "data": base64.b64encode(data).decode("ascii"),
            }
        )

    def resize(self, rows: int, cols: int):
        self._send_message(
            {
                "action": "resize",
                "session_id": self.session_id,
                "rows": rows,
                "cols": cols,
            }
        )

    def close(self):
        if self.sock:
            try:
                if self.session_id:
                    self._send_message(
                        {"action": "close", "session_id": self.session_id}
                    )
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


# EOF
