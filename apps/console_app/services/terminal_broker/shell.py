"""Shell — a single PTY process inside a shared SLURM allocation.

Inherits all PTY lifecycle from ``BasePTY``.  The only difference from
``TerminalSession`` is that Shell takes an external command (e.g.
``srun --overlap --jobid=X ...``) instead of building its own srun.
"""

import os
import socket
import sys
from typing import Optional

from .session import BasePTY

MAX_RESPAWNS = 5


class Shell(BasePTY):
    """PTY shell inside a shared allocation."""

    def __init__(
        self,
        shell_id: str,
        allocation_id: str,
        username: str,
        screen_session: str,
        command: list[str],
    ):
        super().__init__(
            pty_id=shell_id, username=username, screen_session=screen_session
        )
        self.shell_id = shell_id
        self.allocation_id = allocation_id
        self.command = command
        self.client_socket: Optional[socket.socket] = None
        self.last_project_slug: str = ""

    def _prepare_child_env(self) -> dict:
        """Prepare env for srun --overlap shell.

        Preserve HOME so apptainer can find the instance database
        (instances are keyed by the HOME of the process that started them).
        User identity is set up inside the container by the shell command.
        """
        original_home = os.environ.get("HOME", "/root")
        env = super()._prepare_child_env()
        env["HOME"] = original_home
        return env

    def _exec_in_child(self):
        """Execute the provided command in child process."""
        try:
            env = self._prepare_child_env()
            os.execvpe(self.command[0], self.command, env)
        except Exception as e:
            sys.stderr.write(f"\x1b[1;31mFailed to start shell: {e}\x1b[0m\r\n")
            sys.stderr.flush()


# EOF
