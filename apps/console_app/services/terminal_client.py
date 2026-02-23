#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal Broker Client - Async client for WebSocket consumers

This client communicates with the Terminal Broker via Unix socket,
allowing safe PTY operations from within Daphne's asyncio event loop.
"""

import asyncio
import base64
import json
import logging
import struct
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Default socket path (must match broker)
SOCKET_PATH = "/tmp/scitex-terminal-broker.sock"


class TerminalBrokerClient:
    """
    Async client for Terminal Broker.

    Usage:
        client = TerminalBrokerClient()
        await client.connect()
        session_id = await client.spawn(username, user_data_dir, ...)
        await client.send_input(session_id, b"ls -la\n")
        # Output comes via callback set with set_output_callback()
        await client.close()
    """

    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.session_id: Optional[str] = None
        self.output_callback: Optional[Callable[[bytes], None]] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the terminal broker."""
        try:
            self.reader, self.writer = await asyncio.open_unix_connection(
                self.socket_path
            )
            self._connected = True
            logger.debug("Connected to terminal broker")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to terminal broker: {e}")
            return False

    def set_output_callback(self, callback: Callable[[bytes], None]):
        """Set callback for PTY output."""
        self.output_callback = callback

    async def spawn(
        self,
        username: str,
        user_data_dir: Path,
        project_dir: Path,
        container_path: str,
        project_slug: str,
        tmux_session: str = "scitex-0",
    ) -> Optional[str]:
        """
        Spawn a new terminal session.

        Returns session_id on success, None on failure.
        """
        if not self._connected:
            return None

        try:
            await self._send_message(
                {
                    "action": "spawn",
                    "username": username,
                    "user_data_dir": str(user_data_dir),
                    "project_dir": str(project_dir),
                    "container_path": container_path,
                    "project_slug": project_slug,
                    "tmux_session": tmux_session,
                }
            )

            # Start reader task to handle responses
            self._reader_task = asyncio.create_task(self._read_loop())

            # Wait for spawn response
            response = await self._wait_for_response(timeout=10.0)
            if response and response.get("status") == "ok":
                self.session_id = response.get("session_id")
                logger.info(f"Spawned terminal session: {self.session_id}")
                return self.session_id
            else:
                error = (
                    response.get("error", "Unknown error")
                    if response
                    else "No response"
                )
                logger.error(f"Spawn failed: {error}")
                return None

        except Exception as e:
            logger.error(f"Spawn error: {e}")
            return None

    async def send_input(self, data: bytes):
        """Send input to the terminal."""
        if not self._connected or not self.session_id:
            return

        await self._send_message(
            {
                "action": "input",
                "session_id": self.session_id,
                "data": base64.b64encode(data).decode("ascii"),
            }
        )

    async def resize(self, rows: int, cols: int):
        """Resize the terminal."""
        if not self._connected or not self.session_id:
            return

        await self._send_message(
            {
                "action": "resize",
                "session_id": self.session_id,
                "rows": rows,
                "cols": cols,
            }
        )

    async def disconnect_only(self):
        """Disconnect client socket without killing the terminal session.

        The tmux session continues running inside the container (via SLURM).
        A future WebSocket connection can reattach to the same tmux session.
        """
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
            self.writer = None
            self.reader = None

        self.session_id = None
        self._connected = False

    async def close(self):
        """Close the terminal session and connection."""
        if self.session_id:
            try:
                await self._send_message(
                    {
                        "action": "close",
                        "session_id": self.session_id,
                    }
                )
            except:
                pass
            self.session_id = None

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
            self.writer = None
            self.reader = None

        self._connected = False

    async def _send_message(self, msg: dict):
        """Send a length-prefixed JSON message."""
        if not self.writer:
            return

        data = json.dumps(msg).encode("utf-8")
        self.writer.write(struct.pack(">I", len(data)) + data)
        await self.writer.drain()

    async def _read_message(self) -> Optional[dict]:
        """Read a length-prefixed JSON message."""
        if not self.reader:
            return None

        try:
            # Read length
            length_data = await self.reader.readexactly(4)
            msg_length = struct.unpack(">I", length_data)[0]

            if msg_length > 1024 * 1024:  # 1MB limit
                return None

            # Read message
            data = await self.reader.readexactly(msg_length)
            return json.loads(data.decode("utf-8"))

        except asyncio.IncompleteReadError:
            return None
        except Exception as e:
            logger.debug(f"Read error: {e}")
            return None

    async def _read_loop(self):
        """Background task to read messages from broker."""
        try:
            while self._connected:
                msg = await self._read_message()
                if msg is None:
                    break

                action = msg.get("action")
                if action == "output":
                    # PTY output - decode and send to callback
                    if self.output_callback:
                        data = base64.b64decode(msg.get("data", ""))
                        try:
                            self.output_callback(data)
                        except Exception as e:
                            logger.debug(f"Output callback error: {e}")
                elif msg.get("status"):
                    # Response to a command - store for waiting coroutine
                    self._last_response = msg

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Read loop error: {e}")

    async def _wait_for_response(self, timeout: float = 5.0) -> Optional[dict]:
        """Wait for a response message."""
        self._last_response = None
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            if self._last_response is not None:
                response = self._last_response
                self._last_response = None
                return response
            await asyncio.sleep(0.01)

        return None


# Fallback check - can we connect to broker?
async def is_broker_available() -> bool:
    """Check if the terminal broker is running."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(SOCKET_PATH), timeout=1.0
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False
