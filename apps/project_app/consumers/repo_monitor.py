"""
Repository Monitor WebSocket Consumer

Streams real-time filesystem change events from inotifywait to the browser.
Supports filtering, pause/resume, and gitignore integration.
"""

import asyncio
import json
import logging
import re
import shutil
import time
from pathlib import Path

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.project_app.models import Project
from apps.project_app.services.project_service_manager import ProjectServiceManager

logger = logging.getLogger(__name__)

# inotifywait event mapping: raw event name -> normalized name
_EVENT_MAP = {
    "CREATE": "create",
    "MODIFY": "modify",
    "DELETE": "delete",
    "MOVED_TO": "move",
    "MOVED_FROM": None,  # skip move source; MOVED_TO gives destination
}

# Patterns always excluded regardless of user config
_DEFAULT_EXCLUDES = [
    r"\.git/",
    r"__pycache__/",
    r"node_modules/",
    r"\.pyc$",
    r"\.log$",
    r"\.lock$",
]

# Rate-limit: max events buffered before forced flush
_RATE_LIMIT = 50


class RepoMonitorConsumer(AsyncWebsocketConsumer):
    """
    Streams filesystem events from inotifywait over WebSocket.

    Client sends JSON control messages (configure, reconfigure, pause, resume).
    Server sends JSON event messages of type "fs_event" or "error".

    Connection URL: ws/project/repo-monitor/?project_id=<id>
    """

    async def connect(self):
        """Accept connection and resolve project access."""
        self.user = self.scope["user"]
        self.process = None
        self.reader_task = None
        self.paused = False
        self.whitelist_patterns = None
        self._project_path = None

        # Parse query string for project_id
        query_params = dict(
            x.split("=", 1)
            for x in self.scope["query_string"].decode().split("&")
            if "=" in x
        )
        project_id = query_params.get("project_id")

        if not project_id:
            await self.accept()
            await self._send_error("project_id is required")
            await self.close(code=4002)
            return

        if not self.user.is_authenticated:
            await self.accept()
            await self._send_error("Authentication required")
            await self.close(code=4001)
            return

        # Resolve project in a thread (sync ORM)
        project = await asyncio.to_thread(
            lambda: Project.objects.select_related("owner")
            .filter(id=project_id)
            .first()
        )

        if not project:
            await self.accept()
            await self._send_error("Project not found")
            await self.close(code=4004)
            return

        # Access check: owner only for now
        if self.user != project.owner:
            await self.accept()
            await self._send_error("Access denied")
            await self.close(code=4003)
            return

        # Resolve filesystem path
        try:
            project_path = await asyncio.to_thread(
                lambda: ProjectServiceManager(project).get_project_path()
            )
        except Exception as exc:
            await self.accept()
            await self._send_error(f"Cannot resolve project path: {exc}")
            await self.close(code=4005)
            return

        self._project_path = Path(project_path)
        await self.accept()

    async def receive(self, text_data):
        """Handle control messages from client."""
        try:
            msg = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        msg_type = msg.get("type")
        filters = msg.get("filters", {})

        if msg_type == "configure":
            await self._start_watcher(filters)
        elif msg_type == "reconfigure":
            await self._restart_watcher(filters)
        elif msg_type == "pause":
            self.paused = True
        elif msg_type == "resume":
            self.paused = False
        else:
            await self._send_error(f"Unknown message type: {msg_type}")

    async def disconnect(self, close_code):
        """Stop watcher process on disconnect."""
        await self._stop_watcher()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _start_watcher(self, filters: dict):
        """Spawn inotifywait subprocess and start the reader task."""
        if not shutil.which("inotifywait"):
            await self._send_error("inotifywait is not installed on this server")
            return

        exclude_pattern = await asyncio.to_thread(self._build_exclude_pattern, filters)

        # Whitelist (include only matching paths when set)
        whitelist = filters.get("whitelist", [])
        self.whitelist_patterns = (
            [re.compile(p) for p in whitelist] if whitelist else None
        )

        cmd = [
            "inotifywait",
            "-m",
            "-r",
            "--format",
            "%T %e %w%f",
            "--timefmt",
            "%H:%M:%S",
            "--exclude",
            exclude_pattern,
            "-e",
            "create,modify,delete,moved_to,moved_from",
            str(self._project_path),
        ]

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception as exc:
            await self._send_error(f"Failed to start inotifywait: {exc}")
            return

        self.reader_task = asyncio.create_task(self._read_events())

    async def _restart_watcher(self, filters: dict):
        """Stop existing watcher and start a fresh one."""
        await self._stop_watcher()
        await self._start_watcher(filters)

    async def _stop_watcher(self):
        """Terminate subprocess and cancel reader task."""
        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except (asyncio.CancelledError, Exception):
                pass
            self.reader_task = None

        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except (ProcessLookupError, asyncio.TimeoutError, Exception):
                pass
            self.process = None

    async def _read_events(self):
        """Read and forward inotifywait output lines."""
        batch = []
        batch_start = time.monotonic()

        try:
            while True:
                line_bytes = await self.process.stdout.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").strip()
                event_msg = self._parse_line(line)
                if event_msg is None:
                    continue

                if self.paused:
                    continue

                batch.append(event_msg)

                now = time.monotonic()
                elapsed = now - batch_start

                # Flush if batch is full or 0.2 s window elapsed
                if len(batch) >= _RATE_LIMIT or elapsed >= 0.2:
                    for evt in batch:
                        await self.send(text_data=json.dumps(evt))
                    batch = []
                    batch_start = now

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"RepoMonitorConsumer reader error: {exc}")
        finally:
            # Flush remaining
            for evt in batch:
                try:
                    await self.send(text_data=json.dumps(evt))
                except Exception:
                    pass

    def _parse_line(self, line: str):
        """Parse one inotifywait output line into an event dict or None."""
        # Expected format: "HH:MM:SS EVENT_TYPE /absolute/path"
        parts = line.split(" ", 2)
        if len(parts) != 3:
            return None

        timestamp, raw_event, abs_path = parts

        # inotifywait can emit comma-separated events (e.g. "CREATE,ISDIR")
        primary_event = raw_event.split(",")[0]
        normalized = _EVENT_MAP.get(primary_event)

        if normalized is None:
            return None  # unknown or explicitly skipped

        # Convert to relative path
        try:
            rel_path = str(Path(abs_path).relative_to(self._project_path))
        except ValueError:
            rel_path = abs_path

        # Apply whitelist filter
        if self.whitelist_patterns:
            if not any(p.search(rel_path) for p in self.whitelist_patterns):
                return None

        return {
            "type": "fs_event",
            "event": normalized,
            "path": rel_path,
            "timestamp": timestamp,
        }

    def _build_exclude_pattern(self, filters: dict) -> str:
        """Build combined inotifywait --exclude regex from all sources."""
        patterns = list(_DEFAULT_EXCLUDES)

        if filters.get("respect_gitignore", True):
            patterns.extend(self._parse_gitignore(self._project_path))

        for user_pattern in filters.get("blacklist", []):
            patterns.append(re.escape(user_pattern).replace(r"\*", ".*"))

        # Join with | for inotifywait --exclude
        combined = "|".join(f"({p})" for p in patterns)
        return combined or "^$"

    def _parse_gitignore(self, project_path: Path) -> list:
        """Convert .gitignore glob patterns to inotifywait-compatible regex fragments."""
        gitignore = project_path / ".gitignore"
        if not gitignore.exists():
            return []

        result = []
        try:
            for raw_line in gitignore.read_text(errors="replace").splitlines():
                line = raw_line.strip()
                # Skip blank lines and comments
                if not line or line.startswith("#"):
                    continue
                # Negation patterns not supported here
                if line.startswith("!"):
                    continue

                # Convert glob to a rough regex fragment
                # Escape regex metacharacters except * and ?
                fragment = re.sub(r"[.+^${}()|[\]\\]", lambda m: "\\" + m.group(), line)
                fragment = (
                    fragment.replace("**", ".*")
                    .replace("*", "[^/]*")
                    .replace("?", "[^/]")
                )

                # If pattern ends with / it is directory-only
                result.append(fragment)
        except Exception as exc:
            logger.warning(f"Could not parse .gitignore: {exc}")

        return result

    async def _send_error(self, message: str):
        """Send an error message to the client."""
        try:
            await self.send(text_data=json.dumps({"type": "error", "message": message}))
        except Exception:
            pass


# EOF
