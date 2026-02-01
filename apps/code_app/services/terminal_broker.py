#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal Broker - Separate process for PTY management

This broker runs outside of Daphne's asyncio event loop to safely handle:
- pty.fork() without signal conflicts
- Child process reaping (SIGCHLD)
- Clean shutdown

Architecture:
    Daphne (asyncio) ──Unix Socket──> Terminal Broker ──pty.fork()──> srun/shell

Protocol (JSON over Unix socket):
    Request:  {"action": "spawn", "session_id": "...", "username": "...", ...}
    Response: {"status": "ok", "session_id": "..."} or {"status": "error", "error": "..."}
    I/O:      {"action": "input", "session_id": "...", "data": "..."} (base64)
              {"action": "output", "session_id": "...", "data": "..."} (base64)
    Control:  {"action": "resize", "session_id": "...", "rows": N, "cols": M}
              {"action": "close", "session_id": "..."}
"""

import base64
import json
import logging
import os
import pty
import select
import signal
import socket
import struct
import sys
import termios
import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] terminal-broker: %(message)s",
)
logger = logging.getLogger(__name__)

# Socket path
SOCKET_PATH = "/tmp/scitex-terminal-broker.sock"


class TerminalSession:
    """Manages a single PTY session."""

    def __init__(self, session_id: str, username: str, user_data_dir: Path,
                 project_dir: Path, container_path: str, project_slug: str):
        self.session_id = session_id
        self.username = username
        self.user_data_dir = user_data_dir
        self.project_dir = project_dir
        self.container_path = container_path
        self.project_slug = project_slug
        self.pid: Optional[int] = None
        self.fd: Optional[int] = None
        self.client_socket: Optional[socket.socket] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False

    def spawn(self) -> bool:
        """Spawn PTY process."""
        try:
            self.pid, self.fd = pty.fork()

            if self.pid == 0:
                # Child process - exec shell
                self._exec_shell()
                # Never returns on success
                os._exit(1)

            # Parent process
            self.running = True
            logger.info(f"Session {self.session_id}: spawned PID {self.pid}")
            return True

        except Exception as e:
            logger.error(f"Session {self.session_id}: spawn failed: {e}")
            return False

    def _exec_shell(self):
        """Execute shell in child process (called after fork)."""
        try:
            # Reset signal handlers
            for sig in (signal.SIGCHLD, signal.SIGWINCH, signal.SIGPIPE):
                try:
                    signal.signal(sig, signal.SIG_DFL)
                except (ValueError, OSError):
                    pass

            # Import here to avoid issues in parent process
            from apps.code_app.views.terminal.config import (
                SLURM_CONTAINER_PATH,
                SLURM_CPUS,
                SLURM_MEMORY_GB,
                SLURM_PARTITION,
                SLURM_TIME_LIMIT,
                SLURM_USER_DATA_ROOT,
            )

            # Convert Docker paths to host paths for SLURM
            # SLURM jobs run on compute nodes (host), not inside Docker
            # Docker: /app/data/users/{username} -> Host: /opt/scitex/data/users/{username}
            host_user_dir = SLURM_USER_DATA_ROOT / self.username
            host_project_dir = host_user_dir / "proj" / self.project_slug

            # Build environment
            env = os.environ.copy()
            env["HOME"] = f"/home/{self.username}"
            env["USER"] = self.username
            env["LOGNAME"] = self.username
            env["TERM"] = "xterm-256color"
            env["SHELL"] = "/bin/bash"

            # Build srun command (using HOST paths, not Docker paths)
            cmd = [
                "srun",
                f"--partition={SLURM_PARTITION}",
                f"--cpus-per-task={SLURM_CPUS}",
                f"--mem={SLURM_MEMORY_GB}G",
                f"--time={SLURM_TIME_LIMIT}",
                f"--job-name=terminal_{self.username}",
                "--chdir=/tmp",
                "--pty",
                "apptainer", "shell",
                "--containall",
                "--cleanenv",
                "--writable-tmpfs",
                "--hostname", "scitex-cloud",
                "--home", f"{host_user_dir}:/home/{self.username}",
                "--bind", f"{host_project_dir}:/home/{self.username}/proj/{self.project_slug}:rw",
                "--pwd", f"/home/{self.username}/proj/{self.project_slug}",
                self.container_path,
            ]

            os.chdir("/tmp")  # Safe directory for srun
            os.execvpe("srun", cmd, env)

        except Exception as e:
            sys.stderr.write(f"\x1b[1;31mFailed to start shell: {e}\x1b[0m\r\n")
            sys.stderr.flush()

    def start_reader(self, output_callback):
        """Start thread to read PTY output."""
        def reader():
            try:
                while self.running and self.fd is not None:
                    try:
                        r, _, _ = select.select([self.fd], [], [], 0.1)
                        if r:
                            data = os.read(self.fd, 4096)
                            if data:
                                output_callback(self.session_id, data)
                            else:
                                break  # EOF
                    except (OSError, ValueError):
                        break
            except Exception as e:
                logger.debug(f"Session {self.session_id}: reader ended: {e}")
            finally:
                self.running = False

        self.reader_thread = threading.Thread(target=reader, daemon=True)
        self.reader_thread.start()

    def write(self, data: bytes):
        """Write data to PTY."""
        if self.fd is not None:
            try:
                os.write(self.fd, data)
            except OSError as e:
                logger.debug(f"Session {self.session_id}: write error: {e}")

    def resize(self, rows: int, cols: int):
        """Resize PTY window."""
        if self.fd is not None:
            try:
                termios.tcsetwinsize(self.fd, (rows, cols))
            except Exception as e:
                logger.debug(f"Session {self.session_id}: resize error: {e}")

    def close(self):
        """Close session and clean up."""
        self.running = False

        if self.pid and self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            # Reap child
            try:
                os.waitpid(self.pid, os.WNOHANG)
            except ChildProcessError:
                pass

        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

        logger.info(f"Session {self.session_id}: closed")


class TerminalBroker:
    """
    Terminal broker server.

    Manages multiple terminal sessions, handling PTY operations
    in a clean process separate from Daphne's asyncio loop.
    """

    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
        self.sessions: Dict[str, TerminalSession] = {}
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.lock = threading.Lock()

        # Install SIGCHLD handler
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
        # Remove old socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        os.chmod(self.socket_path, 0o666)  # Allow all users to connect
        self.server_socket.listen(100)
        self.running = True

        logger.info(f"Terminal broker listening on {self.socket_path}")

        while self.running:
            try:
                client, _ = self.server_socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client,),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")

    def _handle_client(self, client: socket.socket):
        """Handle a client connection."""
        session_id = None
        try:
            while True:
                # Read message length (4 bytes)
                length_data = client.recv(4)
                if not length_data:
                    break

                msg_length = struct.unpack(">I", length_data)[0]
                if msg_length > 1024 * 1024:  # 1MB limit
                    break

                # Read message
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
            if session_id:
                self._close_session(session_id)
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
        """Handle spawn request."""
        session_id = str(uuid.uuid4())

        try:
            session = TerminalSession(
                session_id=session_id,
                username=msg["username"],
                user_data_dir=Path(msg["user_data_dir"]),
                project_dir=Path(msg["project_dir"]),
                container_path=msg["container_path"],
                project_slug=msg["project_slug"],
            )
            session.client_socket = client

            if not session.spawn():
                return {"status": "error", "error": "Failed to spawn PTY"}

            # Start reader that sends output back to client
            def output_callback(sid, data):
                try:
                    self._send_message(client, {
                        "action": "output",
                        "session_id": sid,
                        "data": base64.b64encode(data).decode("ascii"),
                    })
                except:
                    pass

            session.start_reader(output_callback)

            with self.lock:
                self.sessions[session_id] = session

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
        return None  # No response needed

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

        if session:
            session.close()

    def stop(self):
        """Stop the broker."""
        self.running = False

        # Close all sessions
        with self.lock:
            for session in list(self.sessions.values()):
                session.close()
            self.sessions.clear()

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
    # Set up Django environment
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    main()
