"""Shell — a single PTY process inside a shared SLURM allocation.

Inherits all PTY lifecycle from ``BasePTY``.  The only difference from
``TerminalSession`` is that Shell takes an external command (e.g.
``srun --overlap --jobid=X ...``) instead of building its own srun.
"""

import os
import socket
import sys
from pathlib import Path
from typing import Optional

from .session import BasePTY

MAX_RESPAWNS = 15


class Shell(BasePTY):
    """PTY shell inside a shared allocation."""

    def __init__(
        self,
        shell_id: str,
        allocation_id: str,
        username: str,
        screen_session: str,
        command: list[str],
        project_dir: Optional[Path] = None,
        provider: str = "anthropic-oauth",
        provider_env: Optional[dict] = None,
        project_slug: str = "",
    ):
        super().__init__(
            pty_id=shell_id,
            username=username,
            screen_session=screen_session,
            project_dir=project_dir,
            provider_env=provider_env,
        )
        # Registry-validated provider id this shell was spawned with —
        # used to fail loud on a reattach that requests a DIFFERENT
        # provider (env cannot change on a live PTY).
        self.provider = provider
        self.shell_id = shell_id
        self.allocation_id = allocation_id
        self.command = command
        self.client_socket: Optional[socket.socket] = None
        # Must be known at CONSTRUCTION, not assigned after spawn(): the fork
        # happens inside spawn(), and _prepare_child_env reads this to export
        # SCITEX_PROJECT to the child. A post-spawn assignment is too late and
        # is what left every fresh shell sitting in /tmp.
        self.last_project_slug: str = project_slug
        self._api_token = self._generate_api_token()

    def _prepare_child_env(self) -> dict:
        """Prepare env for srun --overlap shell.

        Preserve HOME so apptainer can find the instance database
        (instances are keyed by the HOME of the process that started them).
        User identity is set up inside the container by the shell command.
        """
        original_home = os.environ.get("HOME", "/root")
        env = super()._prepare_child_env()
        env["HOME"] = original_home
        env["SCITEX_CURRENT_APP"] = "console"
        # The in-container setup script does `cd /home/$USER/proj/$SCITEX_PROJECT`
        # guarded by `[ -n "$SCITEX_PROJECT" ]`, so an unset value silently skips
        # the cd and the shell stays wherever srun left it (/tmp). Nothing else
        # sets this on the shared-allocation path: the library's `--env` flag
        # applies to `apptainer instance start`, not to the later
        # `apptainer exec instance://` used here, which inherits the CALLER env.
        # Set it twice for the same reason provider_env is (see session.py):
        # plain for `exec instance://`, APPTAINERENV_-prefixed to survive
        # --cleanenv on the legacy one-srun-per-tab path.
        if self.last_project_slug:
            env["SCITEX_PROJECT"] = self.last_project_slug
            env["APPTAINERENV_SCITEX_PROJECT"] = self.last_project_slug
        if self._api_token:
            env["SCITEX_API_TOKEN"] = self._api_token
        env["SCITEX_API_URL"] = os.environ.get(
            "SCITEX_API_URL", "http://127.0.0.1:8000"
        )
        return env

    def _generate_api_token(self) -> str:
        """Generate a short-lived JWT for SDK access from Apptainer."""
        try:
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.tokens import RefreshToken

            User = get_user_model()
            user = User.objects.get(username=self.username)
            return str(RefreshToken.for_user(user).access_token)
        except Exception:
            return ""

    def _exec_in_child(self):
        """Execute the provided command in child process."""
        try:
            env = self._prepare_child_env()
            os.execvpe(self.command[0], self.command, env)
        except Exception as e:
            sys.stderr.write(f"\x1b[1;31mFailed to start shell: {e}\x1b[0m\r\n")
            sys.stderr.flush()


# EOF
