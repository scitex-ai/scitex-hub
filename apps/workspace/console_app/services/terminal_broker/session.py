"""Terminal session — PTY lifecycle base class and srun session.

``BasePTY`` holds the common PTY lifecycle code (fork, read, write,
resize, cleanup, respawn).  ``TerminalSession`` adds srun command
building for the legacy one-srun-per-tab mode.
"""

import collections
import enum
import logging
import os
import pty
import select
import signal
import socket
import sys
import termios
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

MAX_RESPAWNS = 15


class SessionState(enum.Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    EXITED = "exited"
    RESPAWNING = "respawning"
    DEAD = "dead"


class BasePTY:
    """Common PTY lifecycle: fork, read, write, resize, cleanup, respawn."""

    def __init__(
        self,
        pty_id: str,
        username: str,
        screen_session: str = "scitex-0",
        project_dir: Optional[Path] = None,
    ):
        self.pty_id = pty_id
        self.username = username
        self.screen_session = screen_session
        # When the PTY is launched from a workspace project, ``project_dir``
        # is the broker-visible (Docker-side) path to that project so the
        # parent ``os.chdir`` lands the pre-fork cwd on the project root.
        # Caller is responsible for passing a path that exists in the
        # broker's filesystem (e.g. ``USER_DATA_ROOT/<user>/proj/<slug>``);
        # if it does not exist at fork time, ``_prepare_child_env`` falls
        # back to ``HOME`` then ``/tmp`` (same escalation as PR #246).
        self.project_dir: Optional[Path] = project_dir
        self.pid: Optional[int] = None
        self.fd: Optional[int] = None
        self.state = SessionState.DEAD
        self.spawn_count: int = 0
        self.last_spawn_time: float = 0
        self.on_exit_callback: Optional[Callable[[str], None]] = None
        self.reader_thread: Optional[threading.Thread] = None
        self._reader_generation: int = 0
        self._scrollback: collections.deque = collections.deque(maxlen=256)

    @property
    def running(self) -> bool:
        return self.state in (SessionState.RUNNING, SessionState.RESPAWNING)

    def spawn(self) -> bool:
        """Fork a PTY and exec in the child.

        After forking, waits briefly to detect immediate child failure.
        If the child exits within ~1s, captures any output as ``last_error``
        and returns False so callers can surface a useful diagnostic message.
        """
        self.state = SessionState.SPAWNING
        self.last_error: str = ""
        try:
            self.pid, self.fd = pty.fork()
            if self.pid == 0:
                self._exec_in_child()
                os._exit(1)

            # Brief early-exit detection: poll the fd for up to 1s.
            # If the child dies immediately (e.g. execvpe fails), read its
            # terminal output and store it so the caller can show diagnostics.
            deadline = time.time() + 1.0
            output_chunks: list[bytes] = []
            while time.time() < deadline:
                try:
                    r, _, _ = select.select([self.fd], [], [], 0.1)
                    if r:
                        chunk = os.read(self.fd, 4096)
                        if chunk:
                            output_chunks.append(chunk)
                        else:
                            break  # EOF — child exited
                except (OSError, ValueError):
                    break  # fd gone — child exited

                # Check if child already gone (non-blocking waitpid)
                try:
                    waited_pid, status = os.waitpid(self.pid, os.WNOHANG)
                except ChildProcessError:
                    waited_pid = self.pid  # already reaped
                    status = 0
                if waited_pid == self.pid:
                    # Child exited — treat as spawn failure
                    captured = b"".join(output_chunks).decode("utf-8", errors="replace")
                    # Strip ANSI escape codes for cleaner log/error messages
                    import re as _re

                    clean = _re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", captured).strip()
                    self.last_error = clean or f"Process exited with status {status}"
                    logger.error(
                        f"PTY {self.pty_id[:8]}: child exited immediately — "
                        f"{self.last_error!r}"
                    )
                    try:
                        os.close(self.fd)
                    except OSError:
                        pass
                    self.fd = None
                    self.pid = None
                    self.state = SessionState.DEAD
                    return False

            self.state = SessionState.RUNNING
            self.spawn_count += 1
            self.last_spawn_time = time.time()
            logger.info(
                f"PTY {self.pty_id[:8]}: spawned PID {self.pid} "
                f"(attempt {self.spawn_count})"
            )
            return True
        except Exception as e:
            logger.error(f"PTY {self.pty_id[:8]}: spawn failed: {e}")
            self.state = SessionState.DEAD
            return False

    def _exec_in_child(self):
        """Override in subclass to exec the appropriate command."""
        raise NotImplementedError

    def _prepare_child_env(self) -> dict:
        """Reset signals and build environment for child process."""
        for sig in (signal.SIGCHLD, signal.SIGWINCH, signal.SIGPIPE):
            try:
                signal.signal(sig, signal.SIG_DFL)
            except (ValueError, OSError):
                pass
        env = os.environ.copy()
        env["HOME"] = f"/home/{self.username}"
        env["USER"] = self.username
        env["LOGNAME"] = self.username
        env["TERM"] = "xterm-256color"
        env["SHELL"] = "/bin/bash"
        # chdir order (host-side bash PS1 \w, plus the cwd srun inherits):
        #   1. self.project_dir — the workspace project root, when set and
        #      reachable by the broker process. This makes the prompt land
        #      on the user's project instead of bare $HOME.
        #   2. env["HOME"] — same fallback as PR #246, used when no project
        #      context is plumbed through (e.g. legacy callers) or when the
        #      project_dir does not exist in the broker filesystem yet.
        #   3. "/tmp" — last-ditch safety so we never raise out of
        #      _prepare_child_env (the apptainer ``--pwd`` flag fixes the
        #      in-container cwd regardless).
        # OSError from a missing/unreadable dir is the documented signal to
        # escalate to the next candidate; it is not a silent error swallow.
        if self.project_dir is not None:
            try:
                os.chdir(str(self.project_dir))
                return env
            except OSError as exc:
                logger.debug(
                    "PTY %s: project_dir %s not chdir-able (%s); falling back to HOME",
                    self.pty_id[:8],
                    self.project_dir,
                    exc,
                )
        try:
            os.chdir(env["HOME"])
        except OSError:
            os.chdir("/tmp")
        return env

    def start_reader(self, output_callback):
        """Start thread to read PTY output. Stops any existing reader first."""
        self._reader_generation += 1
        my_generation = self._reader_generation

        def reader():
            try:
                while (
                    self.state == SessionState.RUNNING
                    and self.fd is not None
                    and self._reader_generation == my_generation
                ):
                    try:
                        r, _, _ = select.select([self.fd], [], [], 0.1)
                        if r:
                            data = os.read(self.fd, 4096)
                            if data:
                                self._scrollback.append(data)
                                output_callback(self.pty_id, data)
                            else:
                                break
                    except (OSError, ValueError):
                        break
            except Exception as e:
                logger.debug(f"PTY {self.pty_id[:8]}: reader ended: {e}")
            finally:
                if self._reader_generation == my_generation:
                    if self.state == SessionState.RUNNING:
                        if self.on_exit_callback:
                            self.on_exit_callback(self.pty_id)

        self.reader_thread = threading.Thread(target=reader, daemon=True)
        self.reader_thread.start()

    def get_scrollback(self) -> bytes:
        """Return stored scrollback buffer contents."""
        return b"".join(self._scrollback)

    def cleanup_fd(self):
        """Close dead fd and reap child process."""
        if self.pid and self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self.pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self.pid = None
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def respawn(self) -> bool:
        """Clean up old fd and spawn a new PTY."""
        self.cleanup_fd()
        return self.spawn()

    def write(self, data: bytes):
        """Write data to PTY."""
        if self.fd is not None:
            try:
                os.write(self.fd, data)
            except OSError as e:
                logger.debug(f"PTY {self.pty_id[:8]}: write error: {e}")

    def resize(self, rows: int, cols: int):
        """Resize PTY window."""
        if self.fd is not None:
            try:
                termios.tcsetwinsize(self.fd, (rows, cols))
            except Exception as e:
                logger.debug(f"PTY {self.pty_id[:8]}: resize error: {e}")

    def close(self):
        """Close and clean up."""
        self.state = SessionState.DEAD
        self.cleanup_fd()
        logger.info(f"PTY {self.pty_id[:8]}: closed")


class TerminalSession(BasePTY):
    """PTY session that builds and execs an srun command (legacy mode)."""

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
        super().__init__(
            pty_id=session_id, username=username, screen_session=screen_session
        )
        self.session_id = session_id
        self.user_data_dir = user_data_dir
        self.project_dir = project_dir
        self.container_path = container_path
        self.project_slug = project_slug
        self.client_socket: Optional[socket.socket] = None

    def _exec_in_child(self):
        """Execute srun command in child process."""
        try:
            env = self._prepare_child_env()

            from apps.workspace.console_app.views.terminal._command_builder import (
                build_srun_cmd,
            )
            from apps.workspace.console_app.views.terminal.config import (
                SLURM_USER_DATA_ROOT,
            )

            host_user_dir = SLURM_USER_DATA_ROOT / self.username
            host_project_dir = host_user_dir / "proj" / self.project_slug

            cmd = build_srun_cmd(
                container_path=self.container_path,
                username=self.username,
                host_user_dir=host_user_dir,
                host_project_dir=host_project_dir,
                project_slug=self.project_slug,
            )
            os.execvpe("srun", cmd, env)
        except Exception as e:
            sys.stderr.write(f"\x1b[1;31mFailed to start shell: {e}\x1b[0m\r\n")
            sys.stderr.flush()


# EOF
