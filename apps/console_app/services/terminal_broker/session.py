"""Terminal session — manages a single PTY inside srun + Apptainer + screen."""

import logging
import os
import pty
import select
import signal
import socket
import sys
import termios
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TerminalSession:
    """Manages a single PTY session."""

    def __init__(
        self,
        session_id: str,
        username: str,
        user_data_dir: Path,
        project_dir: Path,
        container_path: str,
        project_slug: str,
        screen_session: str = "scitex-0",
    ):
        self.session_id = session_id
        self.username = username
        self.user_data_dir = user_data_dir
        self.project_dir = project_dir
        self.container_path = container_path
        self.project_slug = project_slug
        self.screen_session = screen_session
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

            from apps.console_app.views.terminal._command_builder import build_srun_cmd
            from apps.console_app.views.terminal.config import SLURM_USER_DATA_ROOT

            # Convert Docker paths to host paths for SLURM
            host_user_dir = SLURM_USER_DATA_ROOT / self.username
            host_project_dir = host_user_dir / "proj" / self.project_slug

            cmd = build_srun_cmd(
                container_path=self.container_path,
                username=self.username,
                host_user_dir=host_user_dir,
                host_project_dir=host_project_dir,
                project_slug=self.project_slug,
                screen_session=self.screen_session,
            )

            env = os.environ.copy()
            env["HOME"] = f"/home/{self.username}"
            env["USER"] = self.username
            env["LOGNAME"] = self.username
            env["TERM"] = "xterm-256color"
            env["SHELL"] = "/bin/bash"

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


# EOF
