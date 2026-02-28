"""
Real PTY Terminal — WebSocket consumer with full PTY support.

Broker (preferred): Django WS → Terminal Broker → srun → Apptainer → bash
Direct (fallback):  Django WS → pty.fork() → srun → Apptainer → bash
TRIP/Remote:        Django WS → pty.fork() → ssh → remote bash
"""

import asyncio
import logging
import os
import pty
import select
import signal
import termios

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.project_app.models import Project

from .config import USER_DATA_ROOT
from .execution import (
    check_slurm_status,
    exec_slurm_shell,
    select_container,
)
from .workspace import ensure_workspace

logger = logging.getLogger(__name__)

# Check if broker is available at module load
_BROKER_AVAILABLE = None


async def _check_broker():
    """Check if terminal broker is available."""
    global _BROKER_AVAILABLE
    if _BROKER_AVAILABLE is None:
        try:
            from apps.console_app.services.terminal_client import is_broker_available

            _BROKER_AVAILABLE = await is_broker_available()
        except Exception:
            _BROKER_AVAILABLE = False
    return _BROKER_AVAILABLE


# Fallback: SIGCHLD handler for direct pty.fork() mode
def _sigchld_handler(signum, frame):
    """Reap all zombie children without blocking."""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
        except ChildProcessError:
            break


# Only install if not already handled (for fallback mode)
try:
    if signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL:
        signal.signal(signal.SIGCHLD, _sigchld_handler)
except (ValueError, OSError):
    pass


class TerminalConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for PTY terminal.

    Spawns interactive shell via Terminal Broker (preferred) or direct
    pty.fork() (fallback). Uses SLURM + Apptainer for:
    - Security: Container isolation, no root access
    - Fairness: SLURM scheduling, per-user limits
    - Consistency: Same architecture dev/prod/HPC
    """

    async def connect(self):
        """Accept WebSocket connection and spawn PTY"""
        self.user = self.scope["user"]
        # Broker mode attributes
        self.broker_client = None
        # Direct mode attributes (fallback)
        self.pid = None
        self.fd = None
        self.reader_task = None
        self.use_broker = False

        # Get project ID from query params
        query_params = dict(
            (
                x.split("=")
                for x in self.scope["query_string"].decode().split("&")
                if "=" in x
            )
        )
        project_id = query_params.get("project_id")
        self.screen_session = query_params.get(
            "session", query_params.get("tmux_session", "scitex-0")
        )

        if not project_id:
            await self.accept()
            await self.send(text_data="\x1b[1;31m❌ No project specified\x1b[0m\r\n")
            await self.close(code=4002)
            return

        try:
            # project_id=0 means "home project" (used by AI panel console mode)
            if project_id == "0":
                if not self.user.is_authenticated:
                    await self.accept()
                    await self.send(
                        text_data="\x1b[1;31m❌ Authentication required for home terminal\x1b[0m\r\n"
                    )
                    await self.close(code=4001)
                    return
                self.project = await asyncio.to_thread(
                    lambda: Project.objects.select_related("owner")
                    .filter(owner=self.user, is_home=True)
                    .first()
                )
                if not self.project:
                    # Fall back to first owned project
                    self.project = await asyncio.to_thread(
                        lambda: Project.objects.select_related("owner")
                        .filter(owner=self.user)
                        .first()
                    )
                if not self.project:
                    await self.accept()
                    await self.send(
                        text_data="\x1b[1;31m❌ No projects found. Create a project first.\x1b[0m\r\n"
                    )
                    await self.close(code=4002)
                    return
            else:
                self.project = await asyncio.to_thread(
                    Project.objects.select_related("owner").get, id=project_id
                )

            # Check permissions
            if self.user.is_authenticated:
                has_access = self.user == self.project.owner or await asyncio.to_thread(
                    lambda: self.user in self.project.collaborators.all()
                )
            else:
                session = self.scope.get("session", {})
                visitor_project_id = session.get("visitor_project_id")
                has_access = (
                    visitor_project_id and int(project_id) == visitor_project_id
                )

            if not has_access:
                await self.accept()
                await self.send(
                    text_data="\x1b[1;31m❌ Access denied - no permission for this project\x1b[0m\r\n"
                )
                await self.close(code=4001)
                return

        except Project.DoesNotExist:
            await self.accept()
            await self.send(text_data="\x1b[1;31m❌ Project not found\x1b[0m\r\n")
            await self.close(code=4002)
            return

        await self.accept()

        # Join speech channel group so TTS relay can push to this browser
        if self.user.is_authenticated:
            self.speech_group = f"speech_{self.user.username}"
            await self.channel_layer.group_add(self.speech_group, self.channel_name)
        else:
            self.speech_group = None

        # TRIP / Remote: SSH directly into remote machine
        if self.project.project_type == "trip":
            from .trip_spawn import spawn_trip_ssh

            await spawn_trip_ssh(self)
            return
        if self.project.project_type == "remote":
            from .remote_spawn import spawn_remote_ssh

            await spawn_remote_ssh(self)
            return

        # Try broker first, fall back to direct mode
        if await _check_broker():
            logger.info("Using terminal broker for PTY")
            self.use_broker = True
            await self._spawn_via_broker()
        else:
            logger.warning(
                "Terminal broker unavailable, using direct pty.fork() (deprecated)"
            )
            self.use_broker = False
            await self._spawn_direct()

    async def _spawn_via_broker(self):
        """Spawn PTY via Terminal Broker (preferred method)."""
        username = self.project.owner.username
        project_slug = self.project.slug
        user_data_dir = USER_DATA_ROOT / username
        project_dir = user_data_dir / "proj" / project_slug

        await ensure_workspace(user_data_dir, username, project_slug)

        # Auto-generate AI tool configs (cheap no-op if exists)
        await asyncio.to_thread(
            self._ensure_agents_config, project_dir, self.project.name
        )
        await asyncio.to_thread(
            self._ensure_claude_config, user_data_dir, project_dir, self.project.name
        )

        try:
            container_path = await asyncio.to_thread(
                select_container, user_data_dir, project_dir
            )
        except Exception as e:
            from .execution import ContainerNotFoundError

            if isinstance(e, ContainerNotFoundError):
                await self.send(text_data=f"\x1b[1;31m❌ {e}\x1b[0m\r\n")
                await self.close(code=4003)
                return
            raise

        slurm_available, slurm_status = await asyncio.to_thread(check_slurm_status)
        if not slurm_available:
            logger.error(f"SLURM unavailable ({slurm_status})")
            await self.send(
                text_data=f"\x1b[1;31m❌ SLURM unavailable: {slurm_status}\x1b[0m\r\n"
            )
            await self.close(code=4003)
            return

        try:
            from apps.console_app.services.terminal_client import TerminalBrokerClient

            self.broker_client = TerminalBrokerClient()
            if not await self.broker_client.connect():
                raise Exception("Failed to connect to broker")

            # Set output callback to forward to WebSocket
            def on_output(data: bytes):
                asyncio.create_task(
                    self.send(text_data=data.decode("utf-8", errors="replace"))
                )

            self.broker_client.set_output_callback(on_output)

            # Set session state callback to forward as JSON control messages
            # Use custom OSC escape so client can distinguish from terminal output
            def on_session_state(msg: dict):
                import json

                payload = json.dumps(msg)
                asyncio.create_task(self.send(text_data=f"\x1b]9997;{payload}\x07"))

            self.broker_client.set_session_state_callback(on_session_state)

            session_id = await self.broker_client.spawn(
                username=username,
                user_data_dir=user_data_dir,
                project_dir=project_dir,
                container_path=container_path,
                project_slug=project_slug,
                tmux_session=self.screen_session,
            )

            if not session_id:
                raise Exception("Failed to spawn terminal session")

            logger.info(f"Terminal session started via broker: {session_id}")

        except Exception as e:
            logger.error(f"Broker spawn failed: {e}")
            await self.send(
                text_data=f"\x1b[1;31m❌ Failed to start terminal: {e}\x1b[0m\r\n"
            )
            await self.close(code=4003)

    async def _spawn_direct(self):
        """Spawn PTY directly via pty.fork() (fallback, deprecated)."""
        username = self.project.owner.username
        project_slug = self.project.slug
        user_data_dir = USER_DATA_ROOT / username
        project_dir = user_data_dir / "proj" / project_slug

        await ensure_workspace(user_data_dir, username, project_slug)

        # Auto-generate AI tool configs (cheap no-op if exists)
        await asyncio.to_thread(
            self._ensure_agents_config, project_dir, self.project.name
        )
        await asyncio.to_thread(
            self._ensure_claude_config, user_data_dir, project_dir, self.project.name
        )

        try:
            container_path = await asyncio.to_thread(
                select_container, user_data_dir, project_dir
            )
        except Exception as e:
            from .execution import ContainerNotFoundError

            if isinstance(e, ContainerNotFoundError):
                await self.send(text_data=f"\x1b[1;31m❌ {e}\x1b[0m\r\n")
                await self.close(code=4003)
                return
            raise

        slurm_available, slurm_status = await asyncio.to_thread(check_slurm_status)
        if not slurm_available:
            logger.error(f"SLURM unavailable ({slurm_status})")
            await self.close(code=4003)
            return

        # Block signals during PTY fork to prevent "Interrupted system call"
        old_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK,
            {signal.SIGCHLD, signal.SIGWINCH, signal.SIGINT, signal.SIGTERM},
        )

        try:
            self.pid, self.fd = pty.fork()

            if self.pid == 0:
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
                try:
                    exec_slurm_shell(
                        username,
                        user_data_dir,
                        project_dir,
                        container_path,
                        project_slug,
                        screen_session=self.screen_session,
                    )
                except Exception as e:
                    import sys

                    sys.stderr.write(
                        f"\x1b[1;31m❌ Failed to start terminal: {e}\x1b[0m\r\n"
                    )
                    sys.stderr.flush()
                os._exit(1)
        finally:
            if self.pid != 0:
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

        if self.pid != 0:
            self.reader_task = asyncio.create_task(self._read_pty_direct())

    async def _read_pty_direct(self):
        """Read from PTY and send to WebSocket (direct mode)."""
        try:
            while True:
                r, _, _ = await asyncio.to_thread(select.select, [self.fd], [], [], 0.1)
                if r:
                    try:
                        data = await asyncio.to_thread(os.read, self.fd, 4096)
                        if data:
                            await self.send(
                                text_data=data.decode("utf-8", errors="replace")
                            )
                        else:
                            break
                    except OSError:
                        break
        except Exception as e:
            logger.error(f"PTY read error: {e}")
        finally:
            await self.close()

    async def receive(self, text_data):
        """Receive data from WebSocket and write to PTY."""
        try:
            if text_data.startswith("resize:"):
                _, rows, cols = text_data.split(":")
                await self._resize(int(rows), int(cols))
            elif text_data == "restart:":
                if self.use_broker and self.broker_client:
                    await self.broker_client.restart()
            elif text_data == "stop_allocation:":
                if self.use_broker and self.broker_client:
                    username = self.project.owner.username
                    project_slug = self.project.slug
                    await self.broker_client.stop_allocation(username, project_slug)
            else:
                await self._write_input(text_data.encode("utf-8"))
        except Exception as e:
            logger.error(f"PTY write error: {e}")

    async def _write_input(self, data: bytes):
        """Write input to terminal."""
        if self.use_broker and self.broker_client:
            await self.broker_client.send_input(data)
        elif self.fd is not None:
            await asyncio.to_thread(os.write, self.fd, data)

    async def _resize(self, rows: int, cols: int):
        """Resize terminal."""
        if self.use_broker and self.broker_client:
            await self.broker_client.resize(rows, cols)
        elif self.fd is not None:
            try:
                await asyncio.to_thread(termios.tcsetwinsize, self.fd, (rows, cols))
            except Exception as e:
                logger.error(f"PTY resize error: {e}")

    @staticmethod
    def _ensure_agents_config(project_dir, project_name):
        """Create .agents/ config if missing (runs in thread)."""
        from apps.console_app.services.agents_config import ensure_agents_config

        ensure_agents_config(project_dir, project_name=project_name, force=True)

    @staticmethod
    def _ensure_claude_config(user_data_dir, project_dir, project_name):
        """Create .mcp.json + skills if missing (runs in thread)."""
        from apps.console_app.services.agents_config import ensure_claude_config

        ensure_claude_config(
            user_data_dir, project_dir, project_name=project_name, force=True
        )

    async def tts_speak(self, event):
        """Forward TTS speech request to browser via WebSocket.

        The browser terminal intercepts messages prefixed with
        ``\\x1b]9999;speak:`` and plays them via ``/llm/api/tts/``.
        """
        import base64

        text = event.get("text", "")
        if text:
            b64 = base64.b64encode(text.encode()).decode()
            await self.send(text_data=f"\x1b]9999;speak:{b64}\x07")

    async def media_display(self, event):
        """Forward media display request to browser via WebSocket.

        The browser terminal intercepts ``\\x1b]9998;media:`` escapes
        and renders an overlay image/file preview above the terminal.
        """
        import base64
        import json

        media = event.get("media", {})
        if media:
            payload = json.dumps(media)
            b64 = base64.b64encode(payload.encode()).decode()
            await self.send(text_data=f"\x1b]9998;media:{b64}\x07")

    async def disconnect(self, close_code):
        """Clean up on disconnect.

        Broker mode: Only disconnect the client socket. The PTY session
        continues running so the user can reattach later.

        Direct mode (fallback): Kill the PTY process (no persistence).
        """
        # Leave speech channel group
        if getattr(self, "speech_group", None):
            await self.channel_layer.group_discard(self.speech_group, self.channel_name)

        if self.use_broker and self.broker_client:
            # Broker mode: detach only — session persists for reattach
            await self.broker_client.disconnect_only()
            self.broker_client = None
        else:
            # Direct mode cleanup
            if self.reader_task:
                self.reader_task.cancel()

            if self.pid and self.pid > 0:
                try:
                    os.kill(self.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

                try:
                    await asyncio.to_thread(os.waitpid, self.pid, os.WNOHANG)
                except ChildProcessError:
                    pass
                except Exception as e:
                    logger.debug(f"waitpid error (non-critical): {e}")

            if self.fd:
                try:
                    os.close(self.fd)
                except OSError:
                    pass


# EOF
